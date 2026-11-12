"""Tamper attestation for Sentry's blocking and logging configuration.

This is detection, not prevention. Root is held on every machine in the path,
so nothing here can stop a change. What it does is make a change impossible to
make QUIETLY: the daily digest asserts the state positively to the
accountability partner, so silence is no longer available as a cover.

The policy, stated by the owner:

  adding to a blocklist          PERMITTED
  removing from a blocklist      NOT PERMITTED -> notify
  adding to an allowlist         NOT PERMITTED -> notify
  disabling blocking or logging  NOT PERMITTED -> notify
  narrowing the covered devices  NOT PERMITTED -> notify
  anything else changing         treated as suspected tampering -> notify

The baseline lives on the Archivist, deliberately not on Sentry, so a change
on the monitored host cannot rewrite the record of what it used to be.
"""
from __future__ import annotations
import base64, json, shlex, subprocess
from . import config, store

# field path -> policy
#   list_removal_bad : comma-separated set; additions fine, removals alert
#   list_addition_bad: comma-separated set; removals fine, additions alert
#   must_be_one      : must stay '1'
#   must_not_change  : any change at all alerts
POLICY = {
    "advanced/logqueries":   "must_be_one",
    "advanced/logverbosity": "must_not_change",
    "general/enabled":       "must_be_one",
    "general/port":          "must_not_change",
    "acls/default_action":   "must_not_change",
    "forwarding/enabled":    "must_not_change",
    # Losing a whole DNSBL policy is the bluntest possible bypass.
    "dnsbl/policy_uuids":    "list_removal_bad",
}

# DNSBL settings live under a UUID-keyed policy node, dnsbl/<uuid>/<field>.
# The UUID is opaque and could change, so these are matched by trailing
# field name instead of by full path. An earlier version keyed on flat
# paths like "dnsbl/blocklists", found nothing, and silently reported the
# configuration unchanged while monitoring none of it.
SUFFIX_POLICY = {
    "enabled":     "must_be_one",
    "type":        "list_removal_bad",
    "lists":       "list_removal_bad",
    "blocklists":  "list_removal_bad",
    "wildcards":   "list_removal_bad",
    "allowlists":  "list_addition_bad",
    "source_nets": "list_removal_bad",
    "nxdomain":    "must_not_change",
    "address":     "must_not_change",
    "cache_ttl":   "must_not_change",
}


# Standing exception, the owner's, dated 2026-09-12. YouTube stays blocked by
# default as friction; removing exactly these entries from exactly these
# fields (to watch coursework video) does not notify. Nothing else is covered:
# not other domains, not a YouTube string inside a list URL, not allowlist
# additions. Restoring them is always permitted. Keep in agreement with the
# policy table in the owner's operating notes.
EXEMPT_REMOVALS = {
    "wildcards":  {"youtube.com"},
    "blocklists": {"ytimg.com", "youtu.be"},
}


def policy_for(field: str) -> str | None:
    """Resolve the rule for a field path."""
    if field in POLICY:
        return POLICY[field]
    if field.startswith("dnsbl/") and field.count("/") >= 2:
        return SUFFIX_POLICY.get(field.rsplit("/", 1)[1])
    return None

REMOTE_PROBE = r"""
import xml.etree.ElementTree as ET, json
r = ET.parse("/conf/config.xml").getroot()
up = r.find(".//unboundplus")
out = {}
uuids = []

def walk(node, path):
    kids = list(node)
    if not kids:
        out[path] = (node.text or "").strip()
        return
    for k in kids:
        seg = k.tag
        u = k.get("uuid")
        if u:
            uuids.append(u)
            seg = u
        walk(k, path + "/" + seg)

if up is not None:
    for section in ("general", "advanced", "dnsbl", "acls", "forwarding"):
        sec = up.find(section)
        if sec is not None:
            walk(sec, section)
out["dnsbl/policy_uuids"] = ",".join(sorted(set(uuids)))
print(json.dumps(out))
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS attest_baseline(
  field       TEXT PRIMARY KEY,
  value       TEXT NOT NULL,
  captured_at TEXT NOT NULL
);
-- Alerts already pushed and still present. An alert is pushed once, the
-- first run it appears; it stays silent while it persists; if it clears and
-- later comes back, it is pushed again.
CREATE TABLE IF NOT EXISTS attest_standing(
  key         TEXT PRIMARY KEY,
  notified_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attest_finding(
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  detected_at TEXT NOT NULL,
  field       TEXT NOT NULL,
  severity    TEXT NOT NULL,
  detail      TEXT NOT NULL,
  notified    INTEGER NOT NULL DEFAULT 0
);
"""


class Unreachable(RuntimeError):
    pass


def ensure(con) -> None:
    con.executescript(SCHEMA)
    con.commit()


def probe() -> dict:
    """Read the live configuration off Sentry. Read-only."""
    # The probe is base64-encoded so no shell on the path can interpret it.
    # Sentry's root shell is csh and it mangled the Python outright when the
    # source was passed as text through a heredoc.
    b64 = base64.b64encode(REMOTE_PROBE.encode()).decode()
    inner = f'python3 -c "import base64;exec(base64.b64decode(\'{b64}\'))"'
    remote = "sh -c " + shlex.quote(inner)
    cmd = ["ssh", *config.SSH_OPTS, "-i", str(config.SENTRY_SSH_KEY),
           f"{config.SENTRY_USER}@{config.SENTRY_HOST}", remote]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired as e:
        raise Unreachable("ssh timed out probing Sentry") from e
    if r.returncode != 0:
        raise Unreachable(r.stderr.strip()[:300] or "probe failed")
    return json.loads(r.stdout.strip().splitlines()[-1])


def _as_set(v: str) -> set[str]:
    return {p.strip() for p in v.split(",") if p.strip()}


def baseline(con) -> dict:
    ensure(con)
    return {r[0]: r[1] for r in con.execute("SELECT field, value FROM attest_baseline")}


def capture(con, live: dict) -> int:
    """Record the current state as the reference. Use once, knowingly."""
    ensure(con)
    n = 0
    for f, v in live.items():
        con.execute(
            """INSERT INTO attest_baseline(field, value, captured_at) VALUES(?,?,?)
               ON CONFLICT(field) DO UPDATE SET value=excluded.value,
                                                captured_at=excluded.captured_at""",
            (f, v, store.now()))
        n += 1
    con.commit()
    return n


def compare(base: dict, live: dict) -> list[dict]:
    """Return findings. severity is 'alert' or 'note'."""
    findings = []
    for field in sorted(set(base) | set(live)):
        pol = policy_for(field)
        if pol is None:
            continue
        old, new = base.get(field), live.get(field)
        if old is None:
            findings.append({"field": field, "severity": "note",
                             "detail": f"new governed field appeared: {new!r}"})
            continue
        if new is None:
            findings.append({"field": field, "severity": "alert",
                             "detail": "governed field has disappeared "
                                       "from the configuration"})
            continue
        if old == new:
            continue
        if pol == "must_be_one":
            findings.append({"field": field, "severity": "alert",
                             "detail": f"turned off: was {old!r}, now {new!r}"})
        elif pol == "must_not_change":
            findings.append({"field": field, "severity": "alert",
                             "detail": f"changed: was {old!r}, now {new!r}"})
        elif pol == "list_removal_bad":
            o, n_ = _as_set(old), _as_set(live[field])
            gone, added = sorted(o - n_), sorted(n_ - o)
            exempt_set = (EXEMPT_REMOVALS.get(field.rsplit("/", 1)[1], set())
                          if field.startswith("dnsbl/") else set())
            exempt = [g for g in gone if g in exempt_set]
            gone = [g for g in gone if g not in exempt_set]
            if gone:
                findings.append({"field": field, "severity": "alert",
                                 "label": "REMOVED from blocklist", "items": gone,
                                 "detail": f"REMOVED from blocklist: {', '.join(gone)}"})
            if exempt:
                findings.append({"field": field, "severity": "note",
                                 "detail": "removed under the standing YouTube "
                                           f"exception (2026-09-12): {', '.join(exempt)}"})
            if added:
                findings.append({"field": field, "severity": "note",
                                 "detail": f"added (permitted): {', '.join(added)}"})
        elif pol == "list_addition_bad":
            o, n_ = _as_set(old), _as_set(live[field])
            gone, added = sorted(o - n_), sorted(n_ - o)
            if added:
                findings.append({"field": field, "severity": "alert",
                                 "label": "ADDED to allowlist", "items": added,
                                 "detail": f"ADDED to allowlist: {', '.join(added)}"})
            if gone:
                findings.append({"field": field, "severity": "note",
                                 "detail": f"removed from allowlist (permitted): {', '.join(gone)}"})
    # Ungoverned fields still get surfaced, quietly, as suspected tampering
    # material rather than being dropped on the floor.
    for field in sorted(set(live) - set(base)):
        if policy_for(field) is None:
            findings.append({"field": field, "severity": "note",
                             "detail": f"new field appeared: {live[field]!r}"})
    for field in sorted(set(base) - set(live)):
        if policy_for(field) is None:
            findings.append({"field": field, "severity": "alert",
                             "detail": "field removed from configuration"})
    return findings


def record(con, findings: list[dict]) -> None:
    ensure(con)
    for f in findings:
        con.execute(
            """INSERT INTO attest_finding(detected_at, field, severity, detail)
               VALUES(?,?,?,?)""",
            (store.now(), f["field"], f["severity"], f["detail"]))
    con.commit()


def run(con, notify_fn=None) -> dict:
    """Probe, compare, record, and notify on alerts. Returns a summary."""
    ensure(con)
    try:
        live = probe()
    except Unreachable as e:
        store.record_gap(con, "attest_unreachable",
                         f"could not verify Sentry configuration: {e}")
        return {"ok": False, "reason": str(e), "findings": []}

    base = baseline(con)
    if not base:
        n = capture(con, live)
        return {"ok": True, "reason": f"baseline captured ({n} fields)",
                "findings": [], "first_run": True}

    findings = compare(base, live)
    if findings:
        record(con, findings)
    alerts = [f for f in findings if f["severity"] == "alert"]
    fresh = fresh_alerts(con, alerts)
    if fresh and notify_fn:
        body = "\n".join(f"{f['field']}: {f['detail']}" for f in fresh)
        notify_fn("CONFIGURATION CHANGE ON SENTRY\n\n" + body,
                  title="DNS audit: blocking config altered", priority=5,
                  tags="rotating_light")
    if notify_fn:
        # A failed send is queued durably by notify.send, so it still counts
        # as reported. A --quiet run reports nothing and marks nothing.
        mark_standing(con, alerts)
    return {"ok": True, "reason": "", "findings": findings,
            "alerts": len(alerts), "notified": len(fresh) if notify_fn else 0}


def _alert_keys(f: dict) -> list[str]:
    """One key per list entry, so a later removal does not re-announce an
    earlier one; one key per finding otherwise."""
    if "items" in f:
        return [f"{f['field']}|{f['label']}|{i}" for i in f["items"]]
    return [f"{f['field']}|{f['detail']}"]


def fresh_alerts(con, alerts: list[dict]) -> list[dict]:
    """The alerts, trimmed to what has not been pushed while standing."""
    standing = {r[0] for r in con.execute("SELECT key FROM attest_standing")}
    out = []
    for f in alerts:
        if "items" in f:
            new = [i for i in f["items"]
                   if f"{f['field']}|{f['label']}|{i}" not in standing]
            if new:
                out.append({**f, "items": new,
                            "detail": f"{f['label']}: {', '.join(new)}"})
        elif _alert_keys(f)[0] not in standing:
            out.append(f)
    return out


def mark_standing(con, alerts: list[dict]) -> None:
    """Standing = exactly the alerts present now. Cleared ones are dropped,
    so a change that is undone and later redone is pushed again."""
    keys = {k for f in alerts for k in _alert_keys(f)}
    now = store.now()
    con.execute("DELETE FROM attest_standing WHERE key NOT IN (%s)"
                % ",".join("?" * len(keys)) if keys else
                "DELETE FROM attest_standing", tuple(keys))
    for k in keys:
        con.execute("INSERT INTO attest_standing(key, notified_at) VALUES(?,?) "
                    "ON CONFLICT(key) DO NOTHING", (k, now))
    con.commit()
