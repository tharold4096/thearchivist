---
title: "Nightly poweroff: re-enable and manual post-midnight shutdown"
date: 2026-09-23
type: change
status: complete
hosts: [thearchivist]
tags: [power, scheduling, cron, rtc]
summary: "Re-enabled the poweroff cron with the in-place .disabled rename and set the RTC wake alarm by hand to dodge the script's 'tomorrow 07:45' after-midnight bug."
verified: 2026-09-23
open: 0
---

# Nightly poweroff — re-enable and manual post-midnight shutdown

## At a glance

| | |
|---|---|
| **What** | `archivist-nightly-off.disabled` → `archivist-nightly-off`; RTC wake alarm set to today 07:45 |
| **Why** | Restore the schedule and take the host down at 01:17 without skipping a day |
| **Where** | thearchivist · `/etc/cron.d/`, `/sys/class/rtc/rtc0/wakealarm` |
| **Risk** | Running `nightly-poweroff.sh` after midnight sets the wake a day late |
| **Rollback** | `mv` the file back to `.disabled` |
| **Verified** | 2026-09-23: cron count 1; wake alarm read back from the kernel and `/proc/driver/rtc` |

> **Current state (verified 2026-11-12):** Open items carried to [2026-10-13 re-enable](2026-10-13-nightly-poweroff-reenable.md).

## Context

* The nightly poweroff cron had been disabled on 2026-09-22 at 22:13 to keep the Archivist up
  past the 22:55 shutdown. It needed re-enabling, and the host needed to go down at 01:17 on
  2026-09-23 with the normal 07:45 wake.

## What changed

* **Tools/stack:** cron (`/etc/cron.d/archivist-nightly-off`), `/sys/class/rtc/rtc0/wakealarm`,
  `shutdown`.
* **Key steps:**
  * The disable had been done by renaming the file to `archivist-nightly-off.disabled` rather
    than commenting the line out. This is the better method: cron.d ignores any filename
    containing a dot, so the disabled file is inert in place and no out-of-tree backup is
    needed. It replaces the comment-out + `/root/*.bak` approach from 2026-09-17.
  * Re-enabled with `mv /etc/cron.d/archivist-nightly-off.disabled
    /etc/cron.d/archivist-nightly-off`, then reasserted `root:root` and mode `644`.
  * **Set the RTC wake alarm by hand rather than running `nightly-poweroff.sh`.** At 01:14 the
    script's `date -d 'tomorrow 07:45'` resolves to 2026-09-24, which would have skipped a
    whole day. Used `date -d 'today 07:45'` instead (epoch `1790167500`).
  * `shutdown -h +2` with an abort message, leaving a cancel window.
* **Config/scripts:** `nightly-poweroff.sh` unchanged. The cron line is unchanged:
  `55 22 * * * root /usr/local/sbin/nightly-poweroff.sh`.

## Issues hit

* Nothing broke. The post-midnight wake-time trap logged on 2026-09-18 was anticipated and
  worked around rather than hit.
* **Issue: qBittorrent transfer check did not return.**
  Symptom: `curl` against the CT 113 WebUI API returned nothing.
  Root cause: `curl` is not present in the container.
  Fix: not pursued — in-flight torrents resume across a power cycle, so this was informational
  rather than a blocker.

## Verification

* **Pre-shutdown checks, all clear:** no running PVE cluster tasks; no `vzdump`, `apt`, `dpkg`,
  or `homelab-update` processes; `systemctl --failed` empty; no pending systemd jobs.
  Samba in VM 101 reported `No locked files`. `/mnt/pve/archive` at 32% (272G/916G),
  `pve-root` at 28% (18G/67G).
* **Cron re-enabled and verified:** `grep -c '^55 22' /etc/cron.d/archivist-nightly-off`
  printed `1`, and the file is back to `-rw-r--r-- root root`.
* **Wake alarm verified two ways:** `date -d @$(cat /sys/class/rtc/rtc0/wakealarm)` printed
  `Wed Sep 23 07:45:00 AM CDT 2026`; `/proc/driver/rtc` showed `alrm_time: 12:45:00`,
  `alrm_date: 2026-09-23`, `alarm_IRQ: yes`.
* **Attestation ran clean.** CT 107 (dns-audit) was already running this time, so the gap from
  2026-09-17 did not recur. `python3 -m dnsaudit.cli attest` exited 0 with
  "configuration unchanged since baseline" and no recent findings.

## Lessons

* Two open items carried forward, both still unaddressed:
  * `nightly-poweroff.sh` still uses `date -d 'tomorrow 07:45'`. It should pick "today" when
    the current time is before 07:45, so a manual run after midnight is safe. Until it does,
    the script must not be run by hand after midnight.
  * CT 107 still has `onboot: 0`, so it does not come back after a power cycle and the
    attestation cannot run until it is started by hand. It happened to be up this time.
* The `.disabled` rename is now the documented way to skip a night. Prefer it over editing the
  cron line.

---

## Resume line

* Restored and verified a scheduled power-management job on a Proxmox host, validating the
  restored cron entry, RTC wake alarm (kernel and hardware readback), and a clean pre-shutdown
  state across 2 VMs and 15 containers before a controlled power-off.
* Identified and worked around a documented date-arithmetic defect in the shutdown script that
  would have silently skipped a full day of scheduled uptime.
