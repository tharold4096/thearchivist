# dnsaudit attest: YouTube exemption and one-shot alerts

**Date:** 2026-09-26
**Machine(s):** The Archivist (LXC 107, `/opt/dnsaudit/dnsaudit/attest.py`)
**Status:** Complete
**Tags:** DNS, accountability, dnsaudit, ntfy

---

## Why I built this

* The standing YouTube exception (2026-09-12) was written down as policy but
  never implemented: `attest.py` had no `EXEMPT_REMOVALS`, so unblocking YouTube
  for coursework pushed an alert (09-26 11:21 CDT).
* Every attest run re-pushed every unresolved alert, so one change produced a
  push per run until reverted.

## How I built it

* `EXEMPT_REMOVALS` -- `wildcards: youtube.com`, `blocklists: ytimg.com, youtu.be`.
  Only removals of exactly those entries from exactly those fields. They are
  recorded as notes, never alerts.
* New table `attest_standing`: one key per alert (per list entry for list
  fields). `run()` pushes only alerts with no standing key, then sets standing to
  exactly the current alerts.
* `--quiet` runs neither push nor mark.
* Files: [`attest.py`](2026-09-26-attest-youtube-exemption-and-one-shot-alerts/attest.py),
  [diff](2026-09-26-attest-youtube-exemption-and-one-shot-alerts/attest.diff).
  Backup on host: `attest.py.bak-2026-09-26`.

## When it fires (exact rule)

A push happens on a non-quiet run (the 08:15 daily `dnsaudit run`, or a manual
`attest`) **iff** at least one alert is present that was not already pushed while
continuously present since. Concretely:

| Situation | Push? |
|---|---|
| Removing youtube.com (wildcard), ytimg.com, youtu.be | never |
| Any other blocklist/wildcard/list-URL removal, allowlist addition, logging/DNSBL/Unbound off, source_nets narrowed, forwarding or other governed field changed | yes, first run it is seen |
| Same change still present on later runs | no |
| A further change while the first is standing | yes, listing only the new entry |
| Change reverted, later redone | yes, again |
| Push fails to deliver | queued and retried; still counts as reported |
| Sentry unreachable | no push; logged `attest_unreachable` gap |

Changes are detected at run time, not live: a change made and reverted between
two runs is never seen.

## What worked

* 14-scenario test against an in-memory DB matched the table above.
* Post-deploy `attest`: exit 0, YouTube removals shown as exempt notes, no push.

## What I'd do differently

* Tradeoff: a standing violation is now announced once, then silent. The daily
  digest does not restate it, so a silent day after an alert is not proof the
  change was reverted -- `attest` output (exit 3) is.
