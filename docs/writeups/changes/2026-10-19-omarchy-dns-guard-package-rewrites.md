---
title: "sentry-dns-guard: package-rewrite windows"
date: 2026-10-19
type: change
status: complete
hosts: [omarchy]
tags: [accountability, detection, false-positives, pacman, systemd]
summary: "Taught the DNS guard to tell a pacman transaction rewriting watched files with identical content apart from a real bypass, using hook-opened transaction windows."
verified: 2026-11-12
open: 1
---

# sentry-dns-guard: package-rewrite windows

## At a glance

| | |
|---|---|
| **What** | pacman hooks open and close a transaction window; rewrites inside a closed window become a note, not a bypass |
| **Why** | `omarchy update` rewrote five watched files byte-for-byte and the guard pushed 'bypass attempted' |
| **Where** | omarchy · `/etc/pacman.d/hooks/{00-sentry-txn-open,zzz-sentry-txn-close}.hook`, guard state `/var/lib/sentry-dns-guard/txn.json` |
| **Risk** | A forged window could hide a real edit; hand-run markers are refused |
| **Rollback** | Remove the two hooks; restore the previous guard |
| **Verified** | 2026-11-12: deployed; a real update on 2026-11-07 logged `package_rewrite` and pushed a note, not a bypass |

> **Current state (verified 2026-11-12):** **Deployed** (header previously said not yet deployed). New issue: three windows opened on 2026-11-09 never closed cleanly, and the guard re-logs `txn_untrusted` for them on every poll. `/var/log/sentry-dns-guard/events.jsonl` holds 582k lines (56 MB) and grows by ~2k lines an hour. It isn't pushing, so this is log bloat rather than alert noise.

## Context

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

## What changed

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
* **Config/scripts:** [`hosts/clients/omarchy/dns-guard/`](../../../hosts/clients/omarchy/dns-guard)
  (hooks and units). The guard script stays in `omarchy-monitor/dns-guard/`
  because it carries the ntfy topic (`<SET-ON-HOST>`; real value in
  `/usr/local/lib/sentry-dns-guard/sentry-dns-guard.py`).

## Issues hit

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

## Verification

* Sandbox test (temp state dir, stubbed pushes, 15 checks, all pass): rewrite in
  a closed window -> one priority-2 note and no bypass; rewrite after close ->
  bypass; content change in window -> finding; back-dated marker -> untrusted;
  unclosed window -> bypass at the cap; back-to-back windows between polls both
  tracked; future close clamped; hand-run marker refused and pushed.
* Pending on deploy: real-transaction check that the ancestry test passes from a
  hook, and that the next `omarchy update` produces the note and no bypass.

## Follow-ups

Status as of 2026-11-12. Ticked items are closed; the evidence is in *Current state* above or the linked doc.

- [x] Deployed; real `omarchy update` on 2026-11-07 produced a `package_rewrite` note and no bypass.
- [ ] Stop re-logging `txn_untrusted` on every poll for the same stale window (582k lines, 56 MB in `/var/log/sentry-dns-guard/events.jsonl`). Log once per window, and rotate the file.

---

## Resume line

* Eliminated update-driven false positives in a tamper-evident DNS guard by
  bracketing package transactions with libalpm hooks, excusing only
  content-identical rewrites inside freshness-checked, capped windows, keeping
  edit-and-revert detection on all DNS config.
