# ntfy — move all publishers to the alerts topic

**Date:** 2026-10-13
**Machine(s):** thearchivist (192.168.10.202), CT 102 ntfy (192.168.10.203)
**Status:** Complete. Retiring the updates topic on the phone is the only step left.
**Tags:** notifications, ntfy, ops

---

## Why I built this

* The alerts topic was proven end to end on the iPhone during the 2026-10-12 Checkmk rollout. The
  updates topic was never confirmed on the phone (see 2026-09-28). Weekly patch reports and
  thin-pool warnings were going to the unconfirmed one, so they now go to the proven one.
* The responder build (Checkmk → Claude) will post to the same topic, so one subscription
  covers everything.

## How I built it

* **Tools/stack:** ntfy 2.28 ACLs (`ntfy access`), `/usr/local/sbin/homelab-update`,
  `/etc/thinpool-alert.conf`.
* **Key steps:**
  * Added the new ACL **before** switching any publisher, so pushes never failed in between:
    `ntfy access homelab homelab-alerts-<SET-ON-HOST> write-only`.
  * `homelab-update`: backed up to `homelab-update.bak-20261013`, then `sed` to a temp file,
    `diff` (only line 48 `NTFY_URL` changed), `bash -n`, set `root:root 750`, and `mv`.
  * `thinpool-alert.conf`: backed up to `.bak-20261013`, then the same temp-file pattern with
    `600` kept.
  * Scanned the host and all 14 running CTs for the updates topic name. Only the two files above
    used it, and both had already been switched. Then ran
    `ntfy access --reset homelab homelab-updates-<SET-ON-HOST>`.
  * Hardening found during verification: `/var/lib/ntfy/user.db` (users and tokens) was
    `644`. It is now `600 ntfy:ntfy`.
* **Config/scripts:** `../../hosts/ntfy/ntfy-acl.md`, `hosts/thearchivist/homelab-update/homelab-update`,
  `hosts/thearchivist/thinpool-guard/thinpool-alert.conf`. Topic names and tokens stay `<SET-ON-HOST>`.

## What broke

* **Issue: the scan for publishers of the updates topic hung.**
  Symptom: `grep -rl` across `/opt` and `/omd/sites` inside the containers ran for more than 5 minutes.
  Root cause: it searched huge trees (Immich data and Checkmk's `var`).
  Fix: narrowed it to config paths, added `-I`, and set a `timeout` per CT. My first attempt
  to kill the stuck scan used `pkill -f` with a pattern that also matched the shell running
  the kill, so that ssh session ended. Nothing on the host changed. I killed the stuck scan
  by PID instead.

## What worked

* The server config checks out:
  * `base-url http://ntfy.home.arpa`;
  * `upstream-base-url https://ntfy.sh`, which wakes iOS;
  * `auth-default-access deny-all`;
  * `cache-file` with a 72h duration, which covers the nightly poweroff.
* The ACL now gives `checkmk` and `homelab` write-only access to the alerts topic, and `tobias` is admin.
* The `homelab-update` credentials sent a test push that returned HTTP 200, and it **arrived on the iPhone**, confirmed by me.
* `THINPOOL_FORCE=1 thinpool-alert` returned `rc=0`.
* After the `chmod`, the ntfy CLI still read `user.db`, `systemctl is-active ntfy` was `active`, and
  `/v1/health` returned 200.

## What I'd do differently

* Use PIDs, not `pkill -f`, when the pattern also appears in the command doing the killing.
* To do: unsubscribe the old updates topic in the iOS app once the thin-pool test push is
  confirmed. The next real `homelab-update` run is Sunday 2026-10-18 08:15. Check that its report
  lands on the alerts topic.

---

## Resume-ready summary

* Consolidated homelab notifications onto one end-to-end-verified ntfy topic. I granted the new
  ACL before cutting publishers over, scanned 14 containers for stray publishers, and only then
  revoked the old access. I also fixed a token database that was world-readable.
