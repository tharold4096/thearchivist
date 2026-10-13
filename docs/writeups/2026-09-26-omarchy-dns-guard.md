# Omarchy DNS lock and sentry-dns-guard

**Date:** 2026-09-26
**Machine(s):** Omarchy (laptop)
**Status:** In Progress -- enforcement live; guard installed, not yet baselined or enabled
**Tags:** DNS, accountability, hardening, nftables, systemd-resolved, ntfy

---

## Why I built this

* Sentry Gate's Unbound + DNSBL only filters what is asked of it. Omarchy could
  step around it by pointing resolved elsewhere, taking DHCP DNS, using a VPN,
  DoH in the browser, or another browser. None of that should be *impossible*
  (root can undo anything) -- it should be *public*: switching away from
  Sentry DNS pushes to the same ntfy topic as correlator2.py and dnsaudit attest.

## How I built it

* **Enforcement (config, fail closed):**
  * resolved global `DNS=100.116.54.77` (Sentry over Tailscale), `FallbackDNS=` empty.
  * NetworkManager `dns=none`, `systemd-resolved=false` -- no DHCP DNS reaches resolved.
  * Tailscale `--accept-dns=false`; tailnet names come from `/etc/hosts` instead.
  * nftables `inet sentry_dns_lock`: 53/853 allowed only to Sentry (and loopback),
    rejected otherwise for output and forward. Loaded by `sentry-dns-lock.service`,
    which deliberately has no ExecStop.
  * Chromium managed policy: `DnsOverHttpsMode=off`, `BuiltInDnsClientEnabled=false`.
* **Detection:** `sentry-dns-guard.py` (stdlib Python, systemd `Type=notify`,
  `WatchdogSec=60`, `ExecStopPost` reports any non-shutdown stop). Watches the
  config files by content and inode/ctime, live resolver state, direct-DNS
  probes, VPN/tunnel/exit-node use, and alternative browsers. Pacman hook pushes
  browser installs immediately. Failed pushes queue to disk and retry via DoH-by-IP.
* **Config/scripts:** [`2026-09-26-omarchy-dns-guard/`](2026-09-26-omarchy-dns-guard/)
  -- the guard script itself lives in `omarchy-monitor/dns-guard/` and is not
  copied here because it carries the ntfy topic (`<SET-ON-HOST>` in any public copy;
  the real value is in `/usr/local/lib/sentry-dns-guard/sentry-dns-guard.py`).

## What broke

* **Issue: MagicDNS names stop resolving**
  Symptom: `accept-dns=false` removes 100.100.100.100, so `ssh root@sentrygate` fails.
  Root cause: tailnet names were only ever resolved by MagicDNS.
  Fix: `/etc/hosts` entries for sentrygate, towerofpower, samba-vm (`hosts-tailnet.txt`).
  New tailnet machines need a line added (the guard reports the edit).

## Update (same day): generic pushes, portable-browser check

* **Pushes carry no specifics.** Every alert is `omarchy: bypass attempted`
  ("BYPASS ATTEMPTED ON OMARCHY" + time). Others: `bypass ongoing` (every 6h
  while anything is active), `bypass cleared` (only when *nothing* is active any
  more), `monitoring resumed`, `monitoring baseline set`. What tripped it is in
  `/var/log/sentry-dns-guard/events.jsonl` and `sentry-dns-guard status`.
* **One push per new bypass.** A new category, or a new finding inside an active
  one, pushes again even while another bypass is active. A persisting one does
  not repeat until the 6h reminder.
* **New category `portable_browser`**, scanned every 2 min (~0.3 s): browser
  AppImages, browser-named ELF binaries (extracted tarballs, incl. any Chromium
  outside the system path) under /home, /root, /opt, /srv, /tmp, /var/tmp,
  /usr/local, /dev/shm; and per-user flatpaks, which `flatpak list` as root
  misses. Verified against planted fakes; zero hits on the real system.

## What worked

* After each step: `resolvectl dns` shows only `Global: 100.116.54.77`; the
  canary resolves to 0.0.0.0; direct queries to 1.1.1.1/9.9.9.9/8.8.8.8 on 53
  and 853 are rejected; Sentry still answers directly.
* `sentry-dns-guard status`: 0 dns / vpn / browser findings; only "baseline missing".
* Test push delivered 2026-09-26 11:24 CDT.

## What I'd do differently

* Known tradeoff: captive portals (campus Wi-Fi) cannot resolve until Tailscale
  is up, because there is no fallback. Intentional -- fail closed.

## Remaining

1. `sudo sentry-dns-guard init`
2. `sudo systemctl enable --now sentry-dns-guard`
3. Reboot; confirm `resolvectl dns`, `nft list table inet sentry_dns_lock`,
   and `sentry-dns-guard status` are unchanged.

---

## Resume-ready summary

* Built a tamper-evident DNS accountability layer for a Linux laptop: nftables
  egress lock, resolver pinning, and a watchdog-supervised Python monitor that
  reports config drift, VPN use, and browser changes to a push channel with
  durable delivery.
