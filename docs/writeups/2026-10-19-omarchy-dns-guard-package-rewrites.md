# sentry-dns-guard: package-rewrite windows

**Date:** 2026-10-19
**Machine(s):** Omarchy laptop
**Status:** In Progress (built and sandbox-tested; not yet deployed)
**Tags:** accountability, detection, false-positives, pacman, systemd

\---

## Why I built this

* 2026-10-19 13:22 CDT the guard pushed `omarchy: bypass attempted` (reason
  `rewrite`) during an `omarchy update`. Nothing was bypassed: five watched
  files had been rewritten with byte-identical content.
  * `networkmanager` 1.58.1-1 -> 1.58.1-2 replaced `NetworkManager.conf`
    (same content, new inode).
  * The `omarchy-settings` 4.0.5 scriptlet ("Applying Omarchy etc-overrides")
    rewrote `nsswitch.conf` (owned by `filesystem`, not by it),
    `conf.d/omarchy-wifi-powersave.conf`, and two `resolved.conf.d` drop-ins.
* `/etc` paths are pinned by inode/ctime as well as content, so that an edit
  that is later reverted still shows. A package rewrite looks identical to that,
  so every update touching those packages would push a false bypass.
* Fix the detection, not the alert: moving these files to content-only would
  silence it but drop edit-and-revert detection on the DNS config permanently.

## How I built it

* **Tools/stack:** libalpm hooks, the guard's existing Python loop.
* **Key steps:**
  * Two pacman hooks bracket every transaction:
    `00-sentry-txn-open.hook` (PreTransaction) and `zzz-sentry-txn-close.hook`
    (PostTransaction, sorts after every other hook since `systemd-tmpfiles` and
    friends can write `/etc` too). Each runs `sentry-dns-guard txn-open|close`,
    which appends/stamps a window in `/var/lib/sentry-dns-guard/txn.json`.
  * Windows are time-based, not package-based: `nsswitch.conf` was written by a
    package that does not own it, so a "which packages changed" check misses it.
  * A rewrite (content identical to baseline) whose ctime falls inside a trusted
    window is logged as `package_rewrite`. One low-priority (2) push,
    "config rewritten by update", goes out per window once it closes.
* **Lockdown guards on the window itself:**
  * Only rewrites are excused. A content change inside a window is still a
    `config` finding.
  * `txn-open/close` refuse to run unless `/usr/bin/pacman` is an ancestor
    process; a hand-run marker is logged `txn_refused` and pushed as a bypass.
  * The loop trusts a window only if it reads it within 120 s of opening, so a
    back-dated marker written straight into `txn.json` excuses nothing. Windows
    are held in memory only; a guard restart mid-update means rewrites alert.
  * A close marker is clamped to when the loop first saw it (cannot extend a
    window into the future); no window covers more than 30 min.
  * A window that never closes (pacman killed, transaction failed) turns every
    rewrite it excused back into a bypass push (`txn_unclosed`).
* **Known gap, accepted:** root can run a real pacman transaction and edit-and-
  revert a watched file inside it. Bounded to the transaction's length, runtime
  DNS checks keep running throughout, and each such window still produces a push.
  Rewrites from `omarchy-migrate` or anything else outside pacman still alert.
* **Config/scripts:** [`hosts/omarchy/dns-guard/`](../../hosts/omarchy/dns-guard/)
  (hooks and units). The guard script stays in `omarchy-monitor/dns-guard/`
  because it carries the ntfy topic (`<SET-ON-HOST>`; real value in
  `/usr/local/lib/sentry-dns-guard/sentry-dns-guard.py`).

## What broke

* **Issue: repo copy of the guard had drifted from the host.**
  Symptom: `omarchy-monitor/dns-guard/` still had `WATCHDOG_S = 60`.
  Root cause: the 2026-09-28 watchdog fix (watchdog killed the guard under
  memory pressure, false bypass push) was applied on the host only:
  `WatchdogSec=180`, `WATCHDOG_S = 180`, and a watchdog ping before every
  bounded blocking call. Same for `sentry-dns-lock.service`, which gained
  `DefaultDependencies=no` + `After=local-fs.target` to break a boot ordering
  cycle (`Before=systemd-resolved` vs the implicit `After=basic.target`) that
  made systemd drop resolved and dbus.
  Fix: host copies synced back to both repos before this change.

## What worked

* Sandbox test (temp state dir, stubbed pushes, 15 checks, all pass): rewrite in
  a closed window -> one priority-2 note and no bypass; rewrite after close ->
  bypass; content change in window -> finding; back-dated marker -> untrusted;
  unclosed window -> bypass at the cap; back-to-back windows between polls both
  tracked; future close clamped; hand-run marker refused and pushed.
* Pending on deploy: real-transaction check that the ancestry test passes from a
  hook, and that the next `omarchy update` produces the note and no bypass.

\---

## Resume-ready summary

* Eliminated update-driven false positives in a tamper-evident DNS guard by
  bracketing package transactions with libalpm hooks, excusing only
  content-identical rewrites inside freshness-checked, capped windows, keeping
  edit-and-revert detection on all DNS config.
