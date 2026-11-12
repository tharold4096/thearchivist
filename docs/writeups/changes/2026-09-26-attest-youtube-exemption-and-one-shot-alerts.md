---
title: "dnsaudit attest: YouTube exemption and one-shot alerts"
date: 2026-09-26
type: change
status: complete
hosts: [ct107-dns-audit, sentrygate]
tags: [dns, accountability, dnsaudit, ntfy]
summary: "Implemented the standing YouTube exemption as exact-match EXEMPT_REMOVALS and made each unresolved finding push once instead of every run."
verified: 2026-09-26
open: 0
---

# dnsaudit attest: YouTube exemption and one-shot alerts

## At a glance

| | |
|---|---|
| **What** | `attest.py`: `EXEMPT_REMOVALS` added; per-finding one-shot push state |
| **Why** | Coursework YouTube unblock pushed an alert, and every run re-pushed every open alert |
| **Where** | ct107-dns-audit · `/opt/dnsaudit/dnsaudit/attest.py` |
| **Risk** | A standing violation is announced once, then goes quiet |
| **Rollback** | Restore the previous `attest.py` |
| **Verified** | 2026-09-26: 14-scenario test; post-deploy attest exit 0 with exempt notes, no push |

## Context

* The standing YouTube exception (2026-09-12) was written down as policy but
  never implemented: `attest.py` had no `EXEMPT_REMOVALS`, so unblocking YouTube
  for coursework pushed an alert (09-26 11:21 CDT).
* Every attest run re-pushed every unresolved alert, so one change produced a
  push per run until reverted.

## What changed

* `EXEMPT_REMOVALS` -- `wildcards: youtube.com`, `blocklists: ytimg.com, youtu.be`.
  Only removals of exactly those entries from exactly those fields. They are
  recorded as notes, never alerts.
* New table `attest_standing`: one key per alert (per list entry for list
  fields). `run()` pushes only alerts with no standing key, then sets standing to
  exactly the current alerts.
* `--quiet` runs neither push nor mark.
* Files: [`attest.py`](../../../hosts/lxc/ct107-dns-audit/attest.py),
  [diff](../../../hosts/lxc/ct107-dns-audit/attest.diff).
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

## Verification

* 14-scenario test against an in-memory DB matched the table above.
* Post-deploy `attest`: exit 0, YouTube removals shown as exempt notes, no push.

## Lessons

* Tradeoff: a standing violation is now announced once, then silent. The daily
  digest does not restate it, so a silent day after an alert is not proof the
  change was reverted -- `attest` output (exit 3) is.
