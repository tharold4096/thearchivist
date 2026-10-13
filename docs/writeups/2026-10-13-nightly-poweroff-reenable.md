# Nightly poweroff — re-enable

**Date:** 2026-10-13
**Machine(s):** thearchivist (Proxmox host, 192.168.10.202)
**Status:** Complete. First scheduled run is tonight at 22:55 (shutdown at 23:00, wake 07:45).
**Tags:** power, scheduling, ops

---

## Why I built this

* The nightly poweroff had been off since 2026-09-24 (see that writeup). Turning the
  22:55 shutdown / 07:45 wake schedule back on.

## How I built it

* **Tools/stack:** cron (`/etc/cron.d/archivist-nightly-off`).
* **Key steps:**
  * Re-enabled at 17:10 CDT with `mv /etc/cron.d/archivist-nightly-off.disabled
    /etc/cron.d/archivist-nightly-off`, then reasserted `root:root` and mode `644`.
  * Re-enabled before midnight, so tonight's scheduled run computes `tomorrow 07:45`
    correctly. No manual wake alarm was needed.
* **Config/scripts:** `nightly-poweroff.sh` and the cron line are unchanged:
  `55 22 * * * root /usr/local/sbin/nightly-poweroff.sh`.

## What broke

* Nothing.

## What worked

* `ls -l /etc/cron.d/` shows `archivist-nightly-off` as `-rw-r--r-- root root`, and no
  `.disabled` copy remains.
* `grep -c '^55 22' /etc/cron.d/archivist-nightly-off` printed `1`.
* `systemctl is-active cron` printed `active`. `shutdown --show` printed `No scheduled shutdown.`
  This is expected, because the script schedules the shutdown only when it runs.

## What I'd do differently

* Still open from 2026-09-23: `nightly-poweroff.sh` still uses `date -d 'tomorrow 07:45'`.
  Don't run it by hand after midnight.
* The responder (CT 116) and Checkmk (CT 115) go down with the host every night. Alerts
  and responder jobs can't happen from 23:00 to 07:45, and a responder approval token issued
  shortly before 23:00 will expire while the host is off.
* Check tomorrow: `journalctl -t nightly-poweroff -b -1` should show
  `Wake alarm set for ... 07:45:00`, and the host should be back up after 07:45.

---

## Resume-ready summary

* Restored a scheduled power-management job on a Proxmox host with a reversible in-place
  change and verified the restored cron entry.
