# Sure auto-categorization: what's left for you

Everything is installed on **Responder (CT 116)**. The timer is **disabled** and the mode is **dry-run**.
Nothing writes to Sure until you finish step 5.

Where things run:
- **Steps 1–2:** in the browser, at `https://budget.home.arpa`.
- **Steps 3–6:** **inside CT 116 as root.** From the Omarchy terminal:
  `ssh root@192.168.10.202`, then `pct enter 116`. The prompt changes to `root@responder`.

---

## 1. Create categories in Sure (browser)

Go to **Categories** (`https://budget.home.arpa/categories`) and load the **default categories**.
Rename or delete any you won't use. Claude can only choose from what exists here.
Optional: add **Rules** (`/rules`) for your most frequent merchants. Rules are applied first, and the categorizer skips anything already categorized.

## 2. Create a read_write API key (browser)

**Settings → API Key** (`/settings/api_keys`) → new key:
- Name: `responder-categorize`
- Scope: **read_write** (it has to set categories; the code only ever sends `category_id`)

Copy it. It is shown once. Save it in Vaultwarden. **Don't paste it into Claude.**

## 3. Put the key on CT 116 (as root inside CT 116)

Paste this one line. It asks for the key without echoing it, and the key never appears in shell history or `ps`:

```
read -rsp 'Sure key: ' k; echo; printf 'SURE_API_KEY=%s\n' "$k" >> /etc/responder/sure.env; unset k; grep -c '^SURE_API_KEY=' /etc/responder/sure.env
```

It should print **`1`**. If it prints `2`, you added it twice: edit `/etc/responder/sure.env` and keep one line.

## 4. Check, then dry run (as root inside CT 116)

```
/usr/local/sbin/sure-categorize --check
```
Expect: `OK categories=<N> uncategorized_candidates=<about 369> mode=dry-run`
- `SURE_API_KEY is not set` → step 3 didn't land.
- An SSL error → the pinned CA in `/etc/responder/caddy-root.crt` no longer matches Caddy.
- `HTTP Error 401` → wrong key, or it was revoked.
- `categories=0` → step 1 isn't done (exit code 1).

Then the full dry run. It calls Claude in batches of 50 (about 8 calls for 369 transactions, a minute or two) and **writes nothing**:
```
/usr/local/sbin/sure-categorize --dry-run
/usr/local/sbin/sure-categorize --report | less
```
The report has one line per transaction: `date  amount  name  result  confidence  category-or-reason`.
`proposed` lines are what apply mode would set (high + medium confidence). `skipped` lines show why.
Scroll through it. If whole groups are wrong, fix the categories or add rules in Sure, then dry-run again.

## 5. Turn it on (as root inside CT 116), only after the report looks right

```
sed -i 's/^SURE_CATEGORIZE_MODE=.*/SURE_CATEGORIZE_MODE=apply/' /etc/responder/sure.env && systemctl start sure-categorize.service && journalctl -u sure-categorize -n 5 --no-pager
```
This first apply run backfills everything (about 2–4 minutes; it pauses briefly between writes so Sure's worker keeps up).
Expect a journal line like `Sure: categorized <N> of 369 uncategorized (skipped <M>)` and the same text as a low-priority ntfy.

Then enable the daily run (09:00 Central; `Persistent=true` catches up after a late boot):
```
systemctl enable --now sure-categorize.timer && systemctl list-timers sure-categorize.timer --no-pager
```
Expect `NEXT` to be the next 09:00.

## 6. Day to day

- Every morning: a low-priority ntfy with the counts. It's silent on days with nothing new.
- Leftovers (`skipped`): categorize them in the Sure UI. Turning a repeat merchant into a rule stops it showing up again.
- See what a run did: `/usr/local/sbin/sure-categorize --report` (latest), or `ls /var/lib/responder/categorize/`.
- **Undo a run:** `/usr/local/sbin/sure-categorize --revert /var/lib/responder/categorize/report-YYYYMMDD-HHMMSS.json`
  sets that run's categories back to none, except where you've changed them since.
- **Stop it:** `systemctl disable --now sure-categorize.timer`. **Kill switch:** revoke the `responder-categorize` key in Sure.
- Logs: `journalctl -u sure-categorize`.

## What's installed (for reference)

| Path on CT 116 | What |
|---|---|
| `/opt/responder/categorize.py`, `categorize.schema.json`, `categorize-prompt.md` | the job, Claude's output schema, Claude's instructions |
| `/usr/local/lib/responder/run-claude-categorize` | fixed Claude call as `rclaude`, **no tools** |
| `/usr/local/sbin/sure-categorize` | manual helper (above) |
| `/etc/responder/sure.env` (root:responder 640) | config + your key; `rclaude` can't read it (tested) |
| `/etc/responder/caddy-root.crt` | Caddy root CA, pinned for this job only (SHA-256 `BF:E6:D2:69:…:AE:9F:BD`) |
| `/etc/systemd/system/sure-categorize.{service,timer}` | oneshot + daily 09:00 timer |
| `/etc/sudoers.d/responder` | +1 line: `responder` may run the new runner as `rclaude`, no arguments |
| `/var/lib/responder/categorize/` (0700) | reports and Claude transcripts. **Financial data: never journaled to the public repo** |

Source: `~/Projects/homelab/thearchivist/hosts/responder/` (tests: `python3 -m unittest discover -s tests`).
