# Nightly poweroff — one-night skip

**Date:** 2026-09-17
**Machine(s):** thearchivist (Proxmox host, 192.168.10.202)
**Status:** Complete. Restored by hand at 2026-09-18 01:25, ahead of the 08:00 timer.
**Tags:** power, scheduling, ops

---

## Why I built this

* Needed the Archivist to stay up past the 22:55 nightly poweroff for one night only.

## How I built it

* **Tools/stack:** cron (`/etc/cron.d/archivist-nightly-off`), transient systemd timer.
* **Key steps:**
  * Backed up `/etc/cron.d/archivist-nightly-off` to `/root/archivist-nightly-off.bak-2026-09-17`.
    It lives outside `/etc/cron.d` because cron would parse a backup there and still run it.
  * Commented out the `55 22 * * * root /usr/local/sbin/nightly-poweroff.sh` line.
  * `systemd-run --unit=restore-nightly-off --on-calendar="2026-09-18 08:00:00"` copies the
    backup back into place and logs `nightly-poweroff restored` via `logger`.
  * The host has no `atd`, so a transient timer was used in place of `at`.
* **Config/scripts:** `nightly-poweroff.sh` itself was left unchanged.

## What broke

* **Issue: Could not run the blocking-config attestation.**
  Symptom: `pct exec 107` returned `container '107' not running!`.
  Root cause: CT 107 (dns-audit) is stopped and has `onboot: 0`, so it does not come back
  after the nightly power cycle.
  Fix: open. The attestation was not run. This is a logged gap, not a pass.

## What worked

* The cron line is commented and `restore-nightly-off.timer` is listed for Fri 2026-09-18 08:00:00 CDT.
  No shutdown was pending when this was checked at 22:30.

## What I'd do differently

* Add a skip-flag check to `nightly-poweroff.sh`, such as `/run/skip-nightly-poweroff`, so a
  one-night skip doesn't mean editing cron. A file under `/run` also clears itself on reboot.
* Side effects of skipping: tonight's wake alarm isn't re-armed, which doesn't matter because
  the host stays up. The kernel staged for "the 23:00 cycle" won't activate until the next
  cycle that actually runs.
* The restore timer is transient. If the host reboots before 08:00, the timer is lost and the
  cron line stays commented. Check with `grep -c '^55 22' /etc/cron.d/archivist-nightly-off`,
  which should print `1`.

## Follow-up — 2026-09-18 early shutdown

* At 01:20 the host was taken down early. The restore timer was transient, so shutting down
  before 08:00 would have lost it (the risk noted above).
* **Pre-shutdown checks:** no running PVE tasks, vzdump, apt, or homelab-update. The Samba
  session in VM 101 had no locked files. CT 113 was only seeding. No failed units.
  `/mnt/pve/archive` was at 18% and the `data` thin pool at 62%.
* **Restore:** copied `/root/archivist-nightly-off.bak-2026-09-17` back to
  `/etc/cron.d/archivist-nightly-off`. `grep -c '^55 22'` printed `1`.
  Stopped `restore-nightly-off.timer`.
* **Attestation:** started CT 107 for the check. `attest` exited 0 with "configuration
  unchanged since baseline". CT 107 still has `onboot: 0`, so that gap is still open.
* **Wake:** `nightly-poweroff.sh` computes `tomorrow 07:45`, which after midnight means the
  *following* day. The RTC was set by hand to 2026-09-18 07:45 CDT (the RTC read back
  12:45 UTC), then `shutdown -h +1`. The host stopped answering ping at 01:33.
* **Lesson:** don't run `nightly-poweroff.sh` by hand after midnight. It would skip a whole
  day. Either set the RTC by hand or make the script choose "today" when the time is
  before 07:45.
