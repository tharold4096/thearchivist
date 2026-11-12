"""Daily Sure transaction categorizer and renamer (CT 116). Runs as `responder` from sure-categorize.timer.

Claude proposes, this code decides. Claude runs as `rclaude` through the root-owned
run-claude-categorize (no tools at all, fixed flags) and sees only each transaction's date,
direction, amount, current category and name under a short ref, plus the category names. It
never sees the Sure API key or real IDs. Everything it returns is validated here. The only
writes this code can send are:
  - category_id, only while the transaction is still uncategorized
  - name + notes, only while the name is still the raw bank text we read. The raw text is kept
    in notes ("Bank text: ...") so nothing is lost and the transfer trace still sees REF codes.
Transfers between your own accounts are renamed by code (SURE_OWN_ACCOUNTS), not by Claude.

Renaming has its own switch (SURE_RENAME_MODE: off | dry-run | apply) because Sure's CSV import
dedupes on date+amount+name: re-importing a CSV that overlaps renamed rows creates duplicates.
Import longer histories first, then apply renames.

Transaction text is financial data and is attacker-influenceable (merchant names), so:
  - it is wrapped as <untrusted_transactions> and can't forge the tags
  - reports and transcripts stay in /var/lib/responder/categorize (0700); journal.py never
    sees them, so nothing here reaches the public repo
  - ntfy gets counts only

  categorize.py                  modes from SURE_CATEGORIZE_MODE / SURE_RENAME_MODE (dry-run unless "apply")
  categorize.py --dry-run        never writes, whatever the env says
  categorize.py --check          read-only: key, TLS pin and counts; no Claude, no writes
  categorize.py --report [FILE]  print a report (default: the latest)
  categorize.py --transfers      read-only trace: linked pairs, unlinked ones and why, external
  categorize.py --revert FILE    undo a run's renames (and try its categories), where unchanged since

Config comes from the environment (EnvironmentFile=/etc/responder/sure.env, root:responder 640).
"""
import fcntl
import glob
import json
import logging
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import notify

log = logging.getLogger("responder.categorize")

STATE = os.environ.get("CATEGORIZE_STATE", "/var/lib/responder/categorize")
RUNNER = ["sudo", "-n", "-u", "rclaude", "/usr/local/lib/responder/run-claude-categorize"]
TIMEOUT = 330
BATCH = 50
CONFIDENCE = {"low": 0, "medium": 1, "high": 2}
WRITE_PAUSE = 0.25  # each PATCH queues an account sync in Sure; don't flood the worker
RENAME_MODES = ("off", "dry-run", "apply")
BANK_TEXT = "Bank text: "
NAME_MAX = 40
NAME_CHARS = set(" .,&'’*()/#+!:@-")

# Raw bank descriptions (Wells Fargo): card/account/ref numbers, fixed-width padding, or all caps.
RAW_RE = re.compile(r"CARD ?\d{4}|X{4,}\d{4}|REF #|\s{3,}|^[^a-z]{12,}$")
# SimpleFIN names are "<Payee> - <BANK DESCRIPTION>" ("Raising Cane's - PURCHASE RAISING CANE ...").
DESC_START_RE = re.compile(r"[A-Z][A-Z0-9*#&'./]{2,}\b")
TRANSFER_RE = re.compile(r"^(?:ONLINE|RECURRING) TRANSFER (TO|FROM)\b")
LAST4_RE = re.compile(r"X{4,}(\d{4})")
REF_RE = re.compile(r"REF #\s*([A-Z0-9]+)")
EXTERNAL_RE = re.compile(r"^(?:ZELLE|MONEY TRANSFER)\b")


def _untrusted(text):
    # Transaction text can't close or open our delimiter tags, or start a new line.
    return str(text).replace("<", "‹").replace(">", "›").replace("\n", " ").replace("\r", " ")


class SureAPI:
    """The few Sure API calls this job may make. Writes are limited to category_id, name and notes."""

    def __init__(self, base, key, cafile, opener=None):
        self.base = base.rstrip("/")
        self._key = key
        self._ctx = ssl.create_default_context(cafile=cafile)
        self._open = opener or (lambda req: urllib.request.urlopen(req, timeout=20, context=self._ctx))

    def _req(self, method, path, params=None, body=None):
        url = self.base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                     headers={"X-Api-Key": self._key, "Accept": "application/json",
                                              "Content-Type": "application/json"})
        with self._open(req) as resp:
            return json.loads(resp.read().decode())

    def _all(self, path, key, params=None):
        page, out = 1, []
        while True:
            data = self._req("GET", path, {**(params or {}), "page": page, "per_page": 100})
            out += data[key]
            if page >= int(data.get("pagination", {}).get("total_pages", 1) or 1):
                return out
            page += 1

    def categories(self):
        return self._all("/api/v1/categories", "categories")

    def transactions(self):
        return self._all("/api/v1/transactions", "transactions")

    def transaction(self, txn_id):
        return self._req("GET", f"/api/v1/transactions/{urllib.parse.quote(txn_id)}")

    def set_category(self, txn_id, category_id):
        # Sure drops a null category_id (compact_blank), so this can't clear a category.
        return self._req("PATCH", f"/api/v1/transactions/{urllib.parse.quote(txn_id)}",
                         body={"transaction": {"category_id": category_id}})

    def rename(self, txn_id, name, notes):
        # Sure drops a null notes value, so callers pass "" to clear it.
        return self._req("PATCH", f"/api/v1/transactions/{urllib.parse.quote(txn_id)}",
                         body={"transaction": {"name": name, "notes": notes}})


def category_names(categories):
    """{display name: id}. Subcategories show as "Parent > Child"; ambiguous names are dropped."""
    seen, dupes = {}, set()
    for c in categories:
        name = str(c["name"]).strip()
        if c.get("parent"):
            name = f"{str(c['parent']['name']).strip()} > {name}"
        if name in seen:
            dupes.add(name)
        seen[name] = c["id"]
    return {n: i for n, i in seen.items() if n not in dupes}


def candidates(transactions):
    """Uncategorized, not a transfer, not something a person already touched."""
    return [t for t in transactions
            if t.get("category") is None and t.get("transfer") is None and not t.get("user_modified")]


def own_accounts(spec):
    """SURE_OWN_ACCOUNTS -> [(Sure account name, [aliases])].

    Format: "Wells Fargo Savings:1234,WAY2SAVE;Wells Fargo Checking:5678,CLEAR ACCESS".
    A 4-digit alias matches the bank's XXXXXX1234; any other alias is a plain substring.
    """
    out = []
    for part in (spec or "").split(";"):
        name, _, aliases = part.partition(":")
        if name.strip() and aliases.strip():
            out.append((name.strip(), [a.strip().upper() for a in aliases.split(",") if a.strip()]))
    return out


def _account(t):
    return (t.get("account") or {}).get("name", "?")


def own_target(text, own, this_account=None):
    """The own account a transfer description points at, or None."""
    m = LAST4_RE.search(text)
    last4 = m.group(1) if m else None
    for name, aliases in own:
        if name == this_account:
            continue
        for a in aliases:
            if (a.isdigit() and len(a) == 4 and a == last4) or (not a.isdigit() and a in text.upper()):
                return name
    return None


def bank_desc(text):
    """The bank's description without SimpleFIN's "<Payee> - " prefix (CSV names have none)."""
    text = str(text or "")
    payee, sep, desc = text.partition(" - ")
    if sep and re.search(r"[a-z]", payee) and DESC_START_RE.match(desc):
        return desc
    return text


def looks_raw(text):
    text = str(text or "")
    return bool(RAW_RE.search(text) or RAW_RE.search(bank_desc(text)))


def bank_text(t):
    """The original bank description: from our notes marker once renamed, else the name."""
    notes = t.get("notes") or ""
    if BANK_TEXT in notes:
        return bank_desc(notes.split(BANK_TEXT, 1)[1].splitlines()[0])
    return bank_desc(t.get("name"))


def needs_rename(t):
    return (not t.get("user_modified") and BANK_TEXT not in (t.get("notes") or "")
            and looks_raw(t.get("name")))


def transfer_name(t, own):
    """Deterministic name for a transfer description, or None to let Claude name it."""
    text = " ".join(bank_desc(t.get("name")).split())
    m = TRANSFER_RE.match(text)
    if not m:
        return None
    direction = m.group(1).lower()
    target = own_target(text, own, _account(t))
    if target:
        return f"Transfer {direction} {target}"[:NAME_MAX]
    last4 = LAST4_RE.search(text)
    # Not one of SURE_OWN_ACCOUNTS: someone else's account (WF sometimes omits the number).
    return f"Transfer {direction} account …{last4.group(1)}" if last4 else f"Transfer {direction} other account"


def notes_with_bank_text(t):
    raw = BANK_TEXT + " ".join(str(t.get("name") or "").split())
    notes = (t.get("notes") or "").rstrip()
    return f"{notes}\n\n{raw}" if notes else raw


def _name_key(name):
    return re.sub(r"[^0-9a-z]", "", str(name).lower())


def canonical_names(existing, proposed):
    """{key: spelling} so "Kings Church" / "King's Church" / "KINGS CHURCH" all become one.

    A spelling already in Sure wins; otherwise the most frequent proposal (first seen on a tie).
    """
    out = {}
    for n in existing:
        out.setdefault(_name_key(n), n)
    counts = {}
    for n in proposed:
        counts[n] = counts.get(n, 0) + 1
    for n in sorted(counts, key=lambda n: -counts[n]):  # stable: ties keep first-seen order
        out.setdefault(_name_key(n), n)
    return out


def build_prompt(batch, names, wants=None, in_use=()):
    """wants: {ref: "category" | "name" | "category+name"}; default category for every ref.

    in_use: display names already used, so the same merchant gets the same name every time.
    """
    wants = wants or {}
    lines = ["For each bank transaction below, do what its `wants` field asks: pick a category,",
             "a clean display name, or both. Return null for anything not asked for.", "",
             "Categories (use a name exactly as written, or null):"]
    lines += [f"- {n}" for n in sorted(names)]
    if in_use and any("name" in w for w in wants.values()):
        lines += ["", "Display names already in use. When a transaction is the same merchant or payee as one",
                  "of these, reuse that name exactly:", "<untrusted_names_in_use>"]
        lines += [_untrusted(n) for n in sorted(set(in_use))[:400]]
        lines.append("</untrusted_names_in_use>")
    lines += ["", "<untrusted_transactions>"]
    for ref, t in batch:
        cents = int(t.get("signed_amount_cents", 0))
        current = (t.get("category") or {}).get("name") or "none"
        lines.append(_untrusted(f"{ref} | {t.get('date')} | {t.get('classification', '?')}"
                                f" | {cents / 100:.2f} {t.get('currency', '')} | category: {current}"
                                f" | wants: {wants.get(ref, 'category')} | {t.get('name', '')}"))
    lines.append("</untrusted_transactions>")
    return "\n".join(lines)


def _answer_items(verdict, refs):
    """{ref: item} for refs answered exactly once, plus {ref: reason} for the rest; None if unusable."""
    items = verdict.get("assignments") if isinstance(verdict, dict) else None
    if not isinstance(items, list):
        return None
    counts, found = {}, {}
    for a in items:
        if isinstance(a, dict) and isinstance(a.get("ref"), str) and a["ref"] in refs:
            counts[a["ref"]] = counts.get(a["ref"], 0) + 1
            found[a["ref"]] = a
    return {r: a for r, a in found.items() if counts[r] == 1}, {r: "answered more than once" for r in found
                                                                 if counts[r] > 1}


def validate(verdict, refs, names, min_confidence):
    """Split Claude's category answers into (accepted, rejected).

    accepted: {ref: (category_name, confidence)}. Anything not provably fine is rejected
    with a reason: unknown or repeated refs, made-up categories, null, or low confidence.
    """
    answered = _answer_items(verdict, refs)
    if answered is None:
        return {}, {r: "no usable answer" for r in refs}
    found, rejected = answered
    accepted = {}
    for ref, a in found.items():
        cat, conf = a.get("category"), a.get("confidence")
        if cat is None:
            rejected[ref] = "no category fits"
        elif cat not in names:
            rejected[ref] = f"unknown category {str(cat)[:60]!r}"
        elif conf not in CONFIDENCE:
            rejected[ref] = "bad confidence"
        elif CONFIDENCE[conf] < CONFIDENCE[min_confidence]:
            rejected[ref] = f"{conf} confidence"
        else:
            accepted[ref] = (cat, conf)
    for ref in refs:
        if ref not in accepted and ref not in rejected:
            rejected[ref] = "not answered"
    return accepted, rejected


def name_problem(name):
    """None if a proposed display name is acceptable, else why not."""
    if not isinstance(name, str):
        return "no name proposed"
    n = " ".join(name.split())
    if not 2 <= len(n) <= NAME_MAX:
        return "bad length"
    if any(not (c.isalnum() or c in NAME_CHARS) for c in n):
        return "bad characters"
    if re.search(r"\d{5,}", n):
        return "contains a long number"
    if re.search(r"https?:|www\.", n, re.I):
        return "looks like a link"
    if looks_raw(n):
        return "still looks like bank text"
    return None


def validate_names(verdict, refs):
    """(accepted {ref: clean name}, rejected {ref: reason}) for the refs that want a name."""
    answered = _answer_items(verdict, refs)
    if answered is None:
        return {}, {r: "no usable answer" for r in refs}
    found, rejected = answered
    accepted = {}
    for ref, a in found.items():
        problem = name_problem(a.get("name"))
        if problem:
            rejected[ref] = problem
        else:
            accepted[ref] = " ".join(a["name"].split())
    for ref in refs:
        if ref not in accepted and ref not in rejected:
            rejected[ref] = "not answered"
    return accepted, rejected


def ask_claude(prompt, transcript_dir):
    """Run Claude once; returns its structured verdict dict (or None) and keeps a local transcript."""
    started = time.time()
    record = {"started": started, "prompt": prompt}
    try:
        r = subprocess.run(RUNNER, input=prompt.encode(), capture_output=True, timeout=TIMEOUT)
        record.update(rc=r.returncode, stdout=r.stdout.decode(errors="replace"),
                      stderr=r.stderr.decode(errors="replace")[-4000:])
    except subprocess.TimeoutExpired:
        record.update(rc=None, stdout="", stderr="timeout")
    verdict = None
    try:
        out = json.loads(record["stdout"])
        verdict = out.get("structured_output")
        if verdict is None:
            verdict = json.loads(out["result"])
    except (ValueError, KeyError, TypeError):
        verdict = None
    record["seconds"] = round(time.time() - started, 1)
    with open(os.path.join(transcript_dir, f"claude-{int(started * 1000)}.json"), "w") as f:
        json.dump(record, f, indent=1)
    return verdict


def run(api, propose, mode, min_confidence="medium", max_per_run=400, pause=WRITE_PAUSE,
        rename_mode="off", own=()):
    """One pass. propose(prompt) -> verdict dict or None. Returns the report dict."""
    names = category_names(api.categories())
    report = {"started": int(time.time()), "mode": mode, "min_confidence": min_confidence,
              "rename_mode": rename_mode, "categories": len(names), "rows": [], "counts": {},
              "rename_counts": {}}
    if not names:
        report["error"] = "no categories in Sure"
        return report
    txns = api.transactions()
    cat_ids = {t["id"] for t in candidates(txns)}
    fixed, claude_names = {}, set()
    if rename_mode != "off":
        for t in txns:
            if needs_rename(t):
                n = transfer_name(t, own)
                if n:
                    fixed[t["id"]] = n
                else:
                    claude_names.add(t["id"])
    report["uncategorized"] = len(cat_ids)
    report["unnamed"] = len(fixed) + len(claude_names)
    by_date = lambda t: str(t.get("date"))  # noqa: E731
    todo = sorted((t for t in txns if t["id"] in cat_ids or t["id"] in claude_names),
                  key=by_date, reverse=True)[:max_per_run]

    # Ask first, write after: names are made consistent across all batches before anything is applied.
    existing = [str(t["name"]) for t in txns if t.get("name") and not needs_rename(t)]
    in_use = list(existing)
    decided = []  # (t, category answer or None, reason or None, name or None, reason or None)
    for start in range(0, len(todo), BATCH):
        batch = [(f"t{i + 1}", t) for i, t in enumerate(todo[start:start + BATCH])]
        wants = {ref: "+".join(w for w, on in (("category", t["id"] in cat_ids),
                                                ("name", t["id"] in claude_names)) if on)
                 for ref, t in batch}
        verdict = propose(build_prompt(batch, names, wants, in_use))
        cat_refs = {ref: t for ref, t in batch if t["id"] in cat_ids}
        name_refs = {ref: t for ref, t in batch if t["id"] in claude_names}
        accepted, rejected = validate(verdict, cat_refs, names, min_confidence)
        new_names, bad_names = validate_names(verdict, name_refs)
        in_use += new_names.values()
        for ref, t in batch:
            decided.append((t, ref in cat_refs, accepted.get(ref), rejected.get(ref),
                            ref in name_refs, new_names.get(ref), bad_names.get(ref)))
    canonical = canonical_names(existing, in_use[len(existing):])
    offered = {t["id"] for t in todo}
    for t in sorted((t for t in txns if t["id"] in fixed and t["id"] not in offered), key=by_date, reverse=True):
        decided.append((t, False, None, None, False, None, None))

    for t, wants_cat, cat, cat_reason, wants_name, new_name, name_reason in decided:
        row = _row(t)
        if wants_cat:
            _do_category(api, row, t, cat, cat_reason, names, mode, pause)
        if wants_name:
            new_name = canonical.get(_name_key(new_name), new_name) if new_name else None
            _do_rename(api, row, t, new_name, name_reason, rename_mode, pause)
        elif t["id"] in fixed:
            _do_rename(api, row, t, fixed[t["id"]], None, rename_mode, pause)
        report["rows"].append(row)

    for row in report["rows"]:
        if "result" in row:
            report["counts"][row["result"]] = report["counts"].get(row["result"], 0) + 1
        if "rename" in row:
            r = row["rename"]["result"]
            report["rename_counts"][r] = report["rename_counts"].get(r, 0) + 1
    return report


def _row(t):
    return {"id": t["id"], "date": t.get("date"), "name": t.get("name"), "account": _account(t),
            "signed_amount_cents": t.get("signed_amount_cents")}


def _do_category(api, row, t, accepted, reason, names, mode, pause):
    row["previous"] = None
    if accepted is None:
        row.update(result="skipped", reason=reason)
        return
    cat, conf = accepted
    row.update(category=cat, category_id=names[cat], confidence=conf)
    if mode != "apply":
        row["result"] = "proposed"
    else:
        row["result"] = apply_one(api, t["id"], names[cat])
        time.sleep(pause)


def _do_rename(api, row, t, new_name, reason, mode, pause):
    if new_name is None:
        row["rename"] = {"result": "skipped", "reason": reason}
        return
    ren = row["rename"] = {"to": new_name, "notes_before": t.get("notes"), "notes": notes_with_bank_text(t)}
    if mode != "apply":
        ren["result"] = "proposed"
    else:
        ren["result"] = apply_rename(api, t, new_name)
        time.sleep(pause)


def _guarded(txn_id, write):
    try:
        return write()
    except urllib.error.HTTPError as exc:
        # e.g. 422 for split children: Sure said no to this row, not a fault in the run.
        return f"refused {exc.code}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        log.warning("PATCH %s failed: %s", txn_id, exc)
        return "error"


def apply_one(api, txn_id, category_id):
    """Set the category only if the transaction is still uncategorized right now."""
    def write():
        current = api.transaction(txn_id)
        if current.get("category") is not None or current.get("user_modified"):
            return "changed since read"
        api.set_category(txn_id, category_id)
        return "applied"
    return _guarded(txn_id, write)


def apply_rename(api, t, new_name):
    """Rename only if the name is still the raw text we read and nobody touched it since."""
    def write():
        current = api.transaction(t["id"])
        if (current.get("name") != t.get("name") or current.get("user_modified")
                or BANK_TEXT in (current.get("notes") or "")):
            return "changed since read"
        api.rename(t["id"], new_name, notes_with_bank_text(current))
        return "applied"
    return _guarded(t["id"], write)


def revert(api, report):
    """Undo one apply run where nobody has changed the row since. Returns counts.

    Names and notes go back exactly. Categories can't be cleared through Sure's API (it drops a
    null category_id), so each one is tried and checked; ones still set are counted as stuck and
    have to be cleared in the Sure UI.
    """
    done = {"names": 0, "categories": 0, "categories_stuck": 0}
    for row in report["rows"]:
        ren = row.get("rename") or {}
        if ren.get("result") == "applied":
            current = api.transaction(row["id"])
            if current.get("name") == ren["to"]:
                api.rename(row["id"], row["name"], ren.get("notes_before") or "")
                done["names"] += 1
                time.sleep(WRITE_PAUSE)
        if row.get("result") == "applied":
            current = api.transaction(row["id"])
            if (current.get("category") or {}).get("id") != row["category_id"]:
                continue  # someone changed it since; theirs wins
            api.set_category(row["id"], None)
            time.sleep(WRITE_PAUSE)
            if api.transaction(row["id"]).get("category") is None:
                done["categories"] += 1
            else:
                done["categories_stuck"] += 1
    return done


def trace_transfers(txns, own):
    """Read-only. {"linked": [...], "unlinked": [...], "external": [...]} of printable lines."""
    out = {"linked": [], "unlinked": [], "external": []}
    oldest = {}
    for t in txns:
        a = _account(t)
        oldest[a] = min(oldest.get(a, "9999"), str(t.get("date")))
    seen_transfers, seen_refs = set(), set()
    for t in sorted(txns, key=lambda t: str(t.get("date")), reverse=True):
        text = " ".join(bank_text(t).split())
        acct, date = _account(t), str(t.get("date"))
        cents = int(t.get("signed_amount_cents") or 0)
        amount = f"{abs(cents) / 100:>9.2f}"
        ref_m = REF_RE.search(text)
        ref = ref_m.group(1) if ref_m else None
        if t.get("transfer"):
            if t["transfer"].get("id") in seen_transfers:
                continue
            seen_transfers.add(t["transfer"].get("id"))
            other = (t["transfer"].get("other_account") or {}).get("name", "?")
            src, dst = (acct, other) if cents < 0 else (other, acct)
            out["linked"].append(f"{date} {amount}  {src} -> {dst}  ref {ref or '-'}")
            continue
        if TRANSFER_RE.match(text):
            target = own_target(text, own, acct)
            if target:
                if ref and ref in seen_refs:
                    continue
                arrow = f"{acct} -> {target}" if cents < 0 else f"{target} -> {acct}"
                partner = ref and next((o for o in txns if o is not t and _account(o) == target
                                        and ref in bank_text(o)), None)
                if partner:
                    seen_refs.add(ref)
                    why = ("both sides are in Sure but not linked (amounts differ or dates are more than 4 days"
                           " apart): open either one in Sure and use Match transfer")
                elif date < oldest.get(target, "9999"):
                    why = f"other side not in Sure: {target} history starts {oldest.get(target, 'never')}"
                else:
                    why = f"no {target} transaction with the same amount within 4 days of {date}: check {target}"
                out["unlinked"].append(f"{date} {amount}  {arrow}  ref {ref or '-'}\n      {why}")
                continue
            last4 = LAST4_RE.search(text)
            arrow = "out to" if cents < 0 else "in from"
            other = f"account …{last4.group(1)}" if last4 else "other account (no number in bank text)"
            out["external"].append(f"{date} {amount}  {acct} {arrow} {other}  ref {ref or '-'}")
            continue
        if EXTERNAL_RE.match(text):
            arrow = "out" if cents < 0 else "in"
            out["external"].append(f"{date} {amount}  {acct} {arrow}: {str(t.get('name'))[:50]}")
    return out


def print_trace(trace, out=sys.stdout):
    titles = {"linked": "LINKED (Sure counts these as transfers, not spending)",
              "unlinked": "UNLINKED between your own accounts (counted as spending/income until fixed)",
              "external": "EXTERNAL (money to or from other people's accounts)"}
    for key in ("linked", "unlinked", "external"):
        print(f"{titles[key]}: {len(trace[key])}", file=out)
        for line in trace[key]:
            print(f"  {line}", file=out)
        print(file=out)


def print_report(report, out=sys.stdout):
    print(f"mode={report['mode']} rename_mode={report.get('rename_mode', 'off')}"
          f" min_confidence={report['min_confidence']} categories={report['categories']}"
          f" uncategorized={report.get('uncategorized', 0)} unnamed={report.get('unnamed', 0)}"
          f" counts={json.dumps(report['counts'])} rename_counts={json.dumps(report.get('rename_counts', {}))}",
          file=out)
    if report.get("error"):
        print(f"ERROR: {report['error']}", file=out)
    for r in report["rows"]:
        what = r.get("category") or (f"({r.get('reason')})" if "result" in r else "")
        line = (f"{r['date']}  {r['signed_amount_cents'] / 100:>10.2f}  {str(r['name'])[:40]:<40}"
                f"  {r.get('result', '-'):<9} {r.get('confidence', ''):<6} {what}")
        ren = r.get("rename")
        if ren:
            line += f"\n{'':>24}name {ren['result']}: " + (ren.get("to") or f"({ren.get('reason')})")
        print(line, file=out)


def summary(report):
    c = report["counts"]
    if report.get("error"):
        return f"Sure categorize: {report['error']}"
    if report["mode"] == "apply":
        head = f"categorized {c.get('applied', 0)}"
    else:
        head = f"dry run: would categorize {c.get('proposed', 0)}"
    rest = ", ".join(f"{k} {v}" for k, v in sorted(c.items()) if k not in ("applied", "proposed"))
    text = f"Sure: {head} of {report.get('uncategorized', 0)} uncategorized" + (f" ({rest})" if rest else "")
    rc = report.get("rename_counts") or {}
    if rc:
        verb = "renamed" if report.get("rename_mode") == "apply" else "would rename"
        n = rc.get("applied", 0) if report.get("rename_mode") == "apply" else rc.get("proposed", 0)
        text += f"; {verb} {n} of {report.get('unnamed', 0)}"
    return text


def latest_report():
    files = sorted(glob.glob(os.path.join(STATE, "report-*.json")))
    if not files:
        sys.exit("no reports yet")
    return files[-1]


def main(argv):
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    os.umask(0o077)  # reports hold financial data; private even when run by hand outside systemd
    os.makedirs(STATE, mode=0o700, exist_ok=True)

    if argv[:1] == ["--report"]:
        with open(argv[1] if len(argv) > 1 else latest_report()) as f:
            print_report(json.load(f))
        return 0
    if not os.environ.get("SURE_API_KEY"):
        sys.exit("SURE_API_KEY is not set in /etc/responder/sure.env yet")
    api = SureAPI(os.environ["SURE_BASE"], os.environ["SURE_API_KEY"], os.environ["SURE_CA"])
    own = own_accounts(os.environ.get("SURE_OWN_ACCOUNTS"))
    rename_mode = os.environ.get("SURE_RENAME_MODE", "dry-run")
    if rename_mode not in RENAME_MODES:
        sys.exit(f"SURE_RENAME_MODE must be one of {RENAME_MODES}")
    if argv[:1] == ["--check"]:
        # Read-only: proves the key, TLS pin and API shape work. No Claude, no writes.
        names = category_names(api.categories())
        txns = api.transactions()
        print(f"OK categories={len(names)} uncategorized_candidates={len(candidates(txns))}"
              f" rename_candidates={sum(map(needs_rename, txns))} own_accounts={len(own)}"
              f" mode={os.environ.get('SURE_CATEGORIZE_MODE', 'dry-run')} rename_mode={rename_mode}")
        return 0 if names else 1
    if argv[:1] == ["--transfers"]:
        print_trace(trace_transfers(api.transactions(), own))
        return 0
    if argv[:1] == ["--revert"]:
        with open(argv[1]) as f:
            done = revert(api, json.load(f))
        print(f"reverted names={done['names']} categories={done['categories']}")
        if done["categories_stuck"]:
            print(f"{done['categories_stuck']} categories could not be cleared through Sure's API"
                  " (it ignores a null category); clear them in the Sure UI")
        return 0

    dry = "--dry-run" in argv
    mode = "apply" if os.environ.get("SURE_CATEGORIZE_MODE") == "apply" and not dry else "dry-run"
    if dry and rename_mode == "apply":
        rename_mode = "dry-run"
    min_conf = os.environ.get("SURE_MIN_CONFIDENCE", "medium")
    if min_conf not in CONFIDENCE:
        sys.exit(f"SURE_MIN_CONFIDENCE must be one of {sorted(CONFIDENCE)}")

    with open(os.path.join(STATE, ".lock"), "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log.warning("another run is in progress; exiting")
            return 0
        transcripts = os.path.join(STATE, "transcripts")
        os.makedirs(transcripts, mode=0o700, exist_ok=True)
        try:
            report = run(api, lambda p: ask_claude(p, transcripts), mode, min_conf,
                         int(os.environ.get("SURE_MAX_PER_RUN", "400")), rename_mode=rename_mode, own=own)
        except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
            report = {"started": int(time.time()), "mode": mode, "min_confidence": min_conf,
                      "rename_mode": rename_mode, "categories": 0, "rows": [], "counts": {},
                      "error": f"Sure API unreachable or unexpected ({type(exc).__name__}: {str(exc)[:120]})"}
        path = os.path.join(STATE, time.strftime("report-%Y%m%d-%H%M%S.json"))
        with open(path, "w") as f:
            json.dump(report, f, indent=1)

    log.info("%s -> %s", summary(report), path)
    if report["rows"] or report.get("error"):
        notify.publish("Sure categorize", summary(report), priority="low", tags=["moneybag"])
    failed = report["counts"].get("error") or report.get("rename_counts", {}).get("error")
    return 1 if report.get("error") or failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
