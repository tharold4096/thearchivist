# samba-vm fwupd-refresh alert flap

**Date:** 2026-10-21
**Machine(s):** thearchivist (VM 101 samba-vm, CT 116 responder)
**Status:** In Progress (one reset-failed left to run on samba-vm, plus verification)
**Tags:** monitoring, checkmk, responder, alert-noise

---

## Why I built this

* The responder sent a fresh ntfy diagnosis for `samba-vm / Systemd Service Summary` every 40–90 minutes on 2026-10-21. The pushes went out at 08:19, 09:58, 10:45, 11:31 and 12:09, and every one said the same thing: `fwupd-refresh` failed, no action proposed.

## How I built it

* **Tools/stack:** Checkmk systemd summary check → responder (CT 116) → ntfy; `qm guest exec` on samba-vm.
* **Key steps:**
  * Responder log: each CRIT opened a new job and each RECOVERY closed it, so every flap paid for a full diagnosis and push.
  * samba-vm: `fwupd-refresh.timer` fires about every 45–100 min. `fwupdmgr refresh` hangs on "Updating lvfs" for about 2 min and exits 1, which leaves the unit `failed` and makes the summary CRIT.
  * Masked the timer: `systemctl mask --now fwupd-refresh.timer`, then `systemctl reset-failed fwupd-refresh.timer fwupd-refresh.service`.
* **Config/scripts:** host-side only: `/etc/systemd/system/fwupd-refresh.timer -> /dev/null` on samba-vm.

## What broke

* **Issue:** LVFS metadata refresh fails.
  **Symptom:** `curl https://cdn.fwupd.org/...` from samba-vm completes the TLS handshake to Fastly 151.101.114.49 and then stalls (timeout, 0 bytes). The bare IP answers immediately (421), and deb.debian.org and github.com return 200.
  **Root cause:** Upstream of the VM. The Omarchy laptop times out the same way, so this is the Fastly edge or the path through Sentry, not samba-vm. The refresh succeeded every run from 10-11 until it started failing on 10-21.
  **Fix:** None needed for samba-vm. A QEMU guest has no firmware fwupd can update, so the refresh job has no value there. Masked it.
* **Issue:** Masking a timer that has already fired leaves the timer unit itself `failed`, so the summary stays at 1 failed unit until `reset-failed` runs.

## What worked

* After the mask, `systemctl is-enabled fwupd-refresh.timer` prints `masked`.
* Still to verify: `systemctl --failed` on samba-vm prints nothing, and Checkmk's Systemd Service Summary goes OK with no further responder pushes.

## What I'd do differently

* The responder treats each CRIT→OK→CRIT cycle as a brand-new job. Before more hosts are added, flap suppression is worth adding: if the same host/service reopens within N hours and the last diagnosis had no proposal, attach it to that job and skip the push.
