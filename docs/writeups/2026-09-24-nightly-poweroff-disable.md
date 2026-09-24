# Nightly poweroff — disable

**Date:** 2026-09-24
**Machine(s):** thearchivist (Proxmox host, 192.168.10.202)
**Status:** Complete. Cron disabled; re-enable is manual (no restore timer).
**Tags:** power, scheduling, ops

---

## Why I built this

* Needed the Archivist to stay up past the 22:55 nightly poweroff.

## How I built it

* **Tools/stack:** cron (`/etc/cron.d/archivist-nightly-off`).
* **Key steps:**
  * Disabled at 13:11 CDT with `mv /etc/cron.d/archivist-nightly-off
    /etc/cron.d/archivist-nightly-off.disabled`, the documented method from 2026-09-23. cron.d
    ignores filenames containing a dot, so the file is inert in place.
  * No restore timer was set. The host stays up until the cron file is renamed back.
* **Config/scripts:** `nightly-poweroff.sh` and the cron line are unchanged.

## What broke

* Nothing.

## What worked

* `ls -l /etc/cron.d/` shows only `archivist-nightly-off.disabled` (`-rw-r--r-- root root`).
* No other shutdown trigger: `grep -rl nightly-poweroff` across `/etc/cron.d`, `/etc/crontab`
  and `/var/spool/cron` matched only the `.disabled` file; no poweroff/shutdown systemd timers;
  `shutdown --show` printed `No scheduled shutdown.`
* **Attestation ran clean.** CT 107 was running. `attest` exited 0 with "configuration
  unchanged since baseline" and no recent findings.

## What I'd do differently

* To re-enable: `mv /etc/cron.d/archivist-nightly-off.disabled /etc/cron.d/archivist-nightly-off`,
  then `grep -c '^55 22' /etc/cron.d/archivist-nightly-off` should print `1`.
* If the host is shut down by hand after midnight, set the RTC wake alarm by hand. The
  `tomorrow 07:45` defect in `nightly-poweroff.sh` is still open (see 2026-09-23).
* While disabled, the RTC wake alarm isn't re-armed. That doesn't matter while the host stays up.

---

## Resume-ready summary

* Suspended a scheduled power-management job on a Proxmox host with an in-place, reversible
  change, and verified no other shutdown path remained.
