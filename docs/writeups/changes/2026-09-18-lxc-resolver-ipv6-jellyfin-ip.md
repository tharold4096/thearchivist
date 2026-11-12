---
title: "LXC fleet: resolver, IPv6 and Jellyfin address"
date: 2026-09-18
type: change
status: complete
hosts: [thearchivist, ct100-jellyfin, ct103-caddy, sentrygate]
tags: [networking, dns, ipv6, proxmox, lxc]
summary: "Pointed every container at Unbound on Sentry instead of the family router, disabled IPv6 on container eth0 to stop AAAA blackholes, and moved Jellyfin out of the DHCP pool to 192.168.10.207."
verified: 2026-11-12
open: 1
---

# LXC fleet — resolver, IPv6, and Jellyfin address

## At a glance

| | |
|---|---|
| **What** | Host/CT DNS → 192.168.10.1; sysctl drop-in `99-no-ipv6-eth0.conf`; Jellyfin .137 → .207 |
| **Why** | DNS bypassed Sentry, Node apps broke on unreachable IPv6, Jellyfin sat in the DHCP range |
| **Where** | thearchivist · `/etc/pve/lxc/*.conf`, each CT's `/etc/sysctl.d/`, Caddy CT 103 |
| **Risk** | A container left on the old resolver can't resolve `*.home.arpa` |
| **Rollback** | Restore `/root/bak-20260918/` on the host, `Caddyfile.bak-20260918` in CT 103 |
| **Verified** | 2026-11-12, after weeks of nightly power cycles: every CT resolves via 192.168.10.1 and has 0 global IPv6 addresses |

> **Current state (verified 2026-11-12):** The post-power-cycle check this doc owed is **done**: PVE regenerates `resolv.conf` and the drop-in survives boots. Gap: CT 115 (checkmk) and CT 116 (responder) were built after this change and have **no** `99-no-ipv6-eth0.conf`. They currently get no global IPv6, so nothing is broken yet.

## Context

Follow-up to `lxc-dns-ipv6-context.md`. Three faults on the container fleet:

* Every container except qBittorrent resolved through the family router (`192.168.1.1`) instead of Unbound on Sentry Gate, so `*.home.arpa` didn't resolve from inside the containers and DNS bypassed Sentry completely.
* Containers had link-local IPv6 only, but still got AAAA records back. That broke Seerr's TMDB calls.
* Jellyfin's static `192.168.10.137` sat inside Sentry's dnsmasq DHCP pool (`.100–.200`), a lease collision waiting to happen.

## What changed

* **Tools/stack:** `pvesh`, `pct`, sysctl drop-ins, Caddy.
* **Backups first:** `/root/bak-20260918/` on the host holds every `/etc/pve/lxc/*.conf` plus the host `/etc/resolv.conf` from before the change. The Caddyfile backup is `/etc/caddy/Caddyfile.bak-20260918` in CT 103.
* **Resolver:**
  * Host: `pvesh set /nodes/thearchivist/dns --dns1 192.168.10.1 --search home.arpa`.
  * Each CT: `pct set <id> --nameserver 192.168.10.1 --searchdomain home.arpa` on 100, 102–112, 114 and 200, set explicitly so a future host change can't silently redirect them again.
  * Running CTs had the same PVE block written into `/etc/resolv.conf` live. PVE regenerates it from config at the next start.
* **CT 113 deliberately excluded.** It keeps `10.128.0.1` (AirVPN tunnel-only DNS), which is the second fail-closed layer in the arr-stack design. On `.10.1` its tracker lookups would leave via `eth0` from the real IP.
* **IPv6:** [`lxc-dns-ipv6/99-no-ipv6-eth0.conf`](../../../hosts/physical/thearchivist/lxc-dns-ipv6/99-no-ipv6-eth0.conf) goes at `/etc/sysctl.d/` in every CT (live via `sysctl -p`; stopped CTs 105/106/107 written via `pct mount`). Two scoping choices:
  * An in-container file rather than `lxc.sysctl`, because CTs 102, 103 and 200 have snapshot sections and a line appended to their `.conf` would land inside the snapshot.
  * Scoped to `eth0` only: `::1` stays on loopback, and `wg0` on CT 113 is untouched.
* **Jellyfin:** `net0` changed to `ip=192.168.10.207/24` (same MAC and gateway). Caddyfile line 6 now points at `192.168.10.207:8096`.

## Issues hit

* **Issue: "192.168.1.1 on a 192.168.10.0/24 network, works, unexplained" (arr-stack O5)**
  Symptom: containers resolved fine through an address on another subnet.
  Root cause: the containers had no `nameserver` of their own, so they **inherited the host's** `resolv.conf` (`search lan` / `192.168.1.1`). It wasn't DHCP, as first assumed. Traceroute shows `.10.1` → `.1.1`: Sentry routes the query out its WAN (`192.168.1.223`) and the family router answers. CTs 110 and 114 had `192.168.1.1` set explicitly, left over from un-tunnelling them.
  Fix: resolver change above.

* **Issue: Seerr TMDB failures (IPv6)**
  Symptom: bare-colon `[TMDB] Failed to fetch …` errors.
  Root cause, corrected from the context doc: a v6 connect from the container fails **immediately** (`ENETUNREACH` in 23ms). It doesn't hang for 10s. With link-local `fe80::` present, glibc's `AI_ADDRCONFIG` still counts IPv6 as configured and returns AAAA. The 10s Radarr timeout is **not** explained by this and is still open.
  Fix: removing the v6 address on `eth0` takes `getent ahosts api.themoviedb.org` from 8 AAAA records to 0. Node's `https.get` connects over IPv4 in ~150ms. A bare `dns.lookup()` with no hints **still returns AAAA**, so Seerr's `FORCE_IPV4_FIRST=true` has to stay on.

* **Issue: Jellyfin static IP inside the DHCP pool**
  Symptom: none yet, but dnsmasq on Sentry leases `.100–.200` and Jellyfin was pinned at `.137`.
  Fix: moved to `.207`, outside the pool. Direct `.137:8096` clients (TV apps) need re-pointing.

* **Found, not changed: Unbound is not validating DNSSEC.**
  The running `module-config` is `"python iterator"`, with no `validator`. Signed zones return without `ad`, and `sigfail.ippacket.stream` resolves. The design docs say DNSSEC is on. Left for a deliberate decision, because it's a Sentry change. The DNSBL not applying to the Archivist is intentional and was left as is.

## Verification

Verified 2026-09-18, live:

* All 12 non-VPN running CTs: config and live `resolv.conf` both read `192.168.10.1`; `seerr.home.arpa` → `192.168.10.201`; external resolution OK. CT 113 is still on `10.128.0.1`, with the WireGuard handshake fresh and qBittorrent active.
* All 12 running CTs, CT 113 included: 0 IPv6 addresses on `eth0`, and 0 AAAA from `getent ahosts`.
* Jellyfin: `http://192.168.10.207:8096/health` → `Healthy`; `https://jellyfin.home.arpa/health` via Caddy → `200`; `.137` no longer answers.

**Still owed:** re-run the checks below after the next 23:00 → 07:55 power cycle. That proves PVE regenerates `resolv.conf` from the new config and that `systemd-sysctl` reapplies the drop-in at boot.

```
for id in $(pct list | awk 'NR>1 && $2=="running"{print $1}'); do
  printf '%s ' $id; pct exec $id -- sh -c 'awk "/^nameserver/{printf \$2\" \"}" /etc/resolv.conf; ip -6 addr show eth0 | grep -c inet6'
done
# expect: "<id> 192.168.10.1 0" for every CT except 113 → "113 10.128.0.1 0"
```

## Follow-ups

Status as of 2026-11-12. Ticked items are closed; the evidence is in *Current state* above or the linked doc.

- [x] Post-power-cycle check: every running CT resolves via 192.168.10.1 with 0 global IPv6 addresses (2026-11-12).
- [ ] Push `99-no-ipv6-eth0.conf` into CT 115 and CT 116, which were built after this change: `pct push <id> hosts/physical/thearchivist/lxc-dns-ipv6/99-no-ipv6-eth0.conf /etc/sysctl.d/99-no-ipv6-eth0.conf`, then `sysctl --system`.

## Lessons

* Set resolvers explicitly per container at build time, not inherited from the host.
* Pick static addresses against the DHCP range, not by pinning whatever the first lease happened to be.

---

## Resume line

* Traced container DNS silently bypassing the firewall's resolver to inheritance from the hypervisor's own config, then re-pointed a 15-container Proxmox fleet at the internal resolver. The VPN-isolated container kept its fail-closed DNS.
* Diagnosed intermittent Node.js API failures as AAAA records served to IPv6-link-local-only containers, and eliminated AAAA responses fleet-wide with a scoped sysctl.
