---
title: "Nightly poweroff: re-enable"
date: 2026-10-13
type: change
status: complete
hosts: [thearchivist]
tags: [power, scheduling, cron]
summary: "Turned the 22:55 shutdown / 07:45 RTC wake schedule back on after three weeks off."
verified: 2026-11-12
open: 2
---

# Nightly poweroff — re-enable

## At a glance

| | |
|---|---|
| **What** | `archivist-nightly-off.disabled` → `archivist-nightly-off` |
| **Why** | Resume the 23:00–07:45 nightly power-off |
| **Where** | thearchivist · `/etc/cron.d/archivist-nightly-off` → `/usr/local/sbin/nightly-poweroff.sh` |
| **Risk** | Monitoring and the responder are down 23:00–07:45 every night |
| **Rollback** | Rename back to `.disabled` |
| **Verified** | 2026-11-12: cron live; `journalctl -t nightly-poweroff` shows `Wake alarm set for … 07:45` on 11-10 and 11-11 |

> **Current state (verified 2026-11-12):** Schedule is running every night. Both carried defects are **still open**: `nightly-poweroff.sh` line 4 still uses `date -d 'tomorrow 07:45'`, and CT 107 (dns-audit) still has `onboot: 0` and was stopped at check time.

## Context

* The nightly poweroff had been off since 2026-09-24 (see that writeup). Turning the
  22:55 shutdown / 07:45 wake schedule back on.

## What changed

* **Tools/stack:** cron (`/etc/cron.d/archivist-nightly-off`).
* **Key steps:**
  * Re-enabled at 17:10 CDT with `mv /etc/cron.d/archivist-nightly-off.disabled
    /etc/cron.d/archivist-nightly-off`, then reasserted `root:root` and mode `644`.
  * Re-enabled before midnight, so tonight's scheduled run computes `tomorrow 07:45`
    correctly. No manual wake alarm was needed.
* **Config/scripts:** `nightly-poweroff.sh` and the cron line are unchanged:
  `55 22 * * * root /usr/local/sbin/nightly-poweroff.sh`.

## Issues hit

* Nothing.

## Verification

* `ls -l /etc/cron.d/` shows `archivist-nightly-off` as `-rw-r--r-- root root`, and no
  `.disabled` copy remains.
* `grep -c '^55 22' /etc/cron.d/archivist-nightly-off` printed `1`.
* `systemctl is-active cron` printed `active`. `shutdown --show` printed `No scheduled shutdown.`
  This is expected, because the script schedules the shutdown only when it runs.

## Follow-ups

Status as of 2026-11-12. Ticked items are closed; the evidence is in *Current state* above or the linked doc.

- [x] First scheduled cycle ran: `Wake alarm set for … 07:45` logged every night through 2026-11-11.
- [ ] `nightly-poweroff.sh` line 4 still uses `date -d 'tomorrow 07:45'`; pick today when run before 07:45. Until then, never run it by hand after midnight.
- [ ] CT 107 (dns-audit) still `onboot: 0`, so attestation can't run after a power cycle unless started by hand. `pct set 107 --onboot 1` if it should run daily.

## Lessons

* Still open from 2026-09-23: `nightly-poweroff.sh` still uses `date -d 'tomorrow 07:45'`.
  Don't run it by hand after midnight.
* The responder (CT 116) and Checkmk (CT 115) go down with the host every night. Alerts
  and responder jobs can't happen from 23:00 to 07:45, and a responder approval token issued
  shortly before 23:00 will expire while the host is off.
* Check tomorrow: `journalctl -t nightly-poweroff -b -1` should show
  `Wake alarm set for ... 07:45:00`, and the host should be back up after 07:45.

---

## Resume line

* Restored a scheduled power-management job on a Proxmox host with a reversible in-place
  change and verified the restored cron entry.
