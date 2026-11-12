---
title: "sentrygate — Inline firewall, router, DNS filter and Tailscale subnet router for the lab LAN"
date: 2026-07-21
type: host
status: running
hosts: [sentrygate]
tags: [physical]
summary: "Inline firewall, router, DNS filter and Tailscale subnet router for the lab LAN"
verified: 2026-11-12
open: 4
---

# sentrygate

> Everything in the lab reaches the internet, DNS and the tailnet through this 2008 desktop. If it is down the lab is offline, but the family network is not: it hangs off the home router, not this box.

## At a glance

| | |
|---|---|
| **Role** | Inline firewall, router, DNS filter and Tailscale subnet router for the lab LAN |
| **Kind** | Physical machine |
| **OS** | OPNsense 26.7.8_2 (FreeBSD) |
| **Address** | 192.168.1.223/24 (bge0), 192.168.10.1/24 (em0), 100.116.54.77 (tailscale0) |
| **Resources** | Dell Inspiron 530 (2008), Core 2, ~3 GB DDR2, PNY CS900 250 GB SSD |
| **Web UI** | <https://192.168.10.1> |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | Checkmk, Wazuh agent 001 |
| **Backed up by** | OPNsense config export (kept off-repo; never committed) |

## Interfaces

| Name | Role | Address | Notes |
|---|---|---|---|
| `bge0` | WAN | 192.168.1.223/24 | 1000baseT |
| `em0` | LAN | 192.168.10.1/24 | Onboard 82562V-2 is 10/100 only: caps the lab at ~90 Mbit/s |
| `tailscale0` | VPN | 100.116.54.77 |  |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 22 | tcp | sshd | all | tailscale |
| 53 | tcp/udp | Unbound DNS + DNSBL | all | direct |
| 67 | udp | dnsmasq DHCP | all | direct |
| 80 | tcp | OPNsense web UI (redirect) | all | direct |
| 123 | udp | ntpd | all | direct |
| 161 | udp | snmpd (SNMPv3, Checkmk) | 192.168.10.1 | direct |
| 443 | tcp | OPNsense web UI | all | tailscale |
| 3493 | tcp | upsd (NUT server) | 192.168.10.1 | direct |
| 41641 | udp | tailscaled | all | direct |

## Depends on / needed by

- **Needs:** nothing in the lab
- **Needed by:** [thearchivist](../thearchivist/README.md), [ct100-jellyfin](../../lxc/ct100-jellyfin/README.md), [ct102-ntfy](../../lxc/ct102-ntfy/README.md), [ct103-caddy](../../lxc/ct103-caddy/README.md), [ct104-wazuh](../../lxc/ct104-wazuh/README.md), [ct105-nuclei-scanner](../../lxc/ct105-nuclei-scanner/README.md), [ct107-dns-audit](../../lxc/ct107-dns-audit/README.md), [ct108-immich](../../lxc/ct108-immich/README.md), [ct115-checkmk](../../lxc/ct115-checkmk/README.md), [ct116-responder](../../lxc/ct116-responder/README.md), [ct200-vaultwarden](../../lxc/ct200-vaultwarden/README.md), [vm101-samba](../../vm/vm101-samba/README.md), [vm106-budget](../../vm/vm106-budget/README.md), [vm150-pbs](../../vm/vm150-pbs/README.md), [omarchy](../../clients/omarchy/README.md)

## Configuration in this repo

| File | Deployed to | What it does |
|---|---|---|
| [`newsyslog-unbound-dnsbl.conf`](newsyslog-unbound-dnsbl.conf) | `/usr/local/etc/newsyslog.conf.d/` | Rotation for the bridge's JSON log |
| [`ossec_config.d/`](ossec_config.d/) | Wazuh agent config fragments | Client buffer sizing (010) and the DNSBL localfile (020) |
| [`unbound-dnsbl-wazuh.py`](unbound-dnsbl-wazuh.py) | `/usr/local/bin/unbound-dnsbl-wazuh.py` | Bridge daemon: reads Unbound's DNSBL FIFO and writes JSON lines Wazuh can decode |
| [`unbound_dnsbl_wazuh.rc`](unbound_dnsbl_wazuh.rc) | `/usr/local/etc/rc.d/unbound_dnsbl_wazuh` | rc.d script that runs the bridge at boot |

## Operating it

```sh
ssh root@sentrygate                 # over Tailscale
opnsense-version; swapinfo -h
/var/ossec/bin/wazuh-control status
pfctl -ss | wc -l                   # state count
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-10-15 | change | [Sentry DNSBL allowlist for the CSCE 3550 gradebot](../../../docs/writeups/changes/2026-10-15-sentrygate-allowlist-gradebot.md) | complete |
| 2026-10-13 | build | [Responder phase 2: iOS ntfy approval-button spike](../../../docs/writeups/builds/2026-10-13-responder-phase2-ios-approval-spike.md) | complete |
| 2026-10-12 | build | [Checkmk rollout: host, guests, firewall, web UIs, phone alerts](../../../docs/writeups/builds/2026-10-12-checkmk-rollout.md) | complete |
| 2026-09-26 | build | [Omarchy DNS lock and sentry-dns-guard](../../../docs/writeups/builds/2026-09-26-omarchy-dns-guard.md) | complete |
| 2026-09-26 | change | [dnsaudit attest: YouTube exemption and one-shot alerts](../../../docs/writeups/changes/2026-09-26-attest-youtube-exemption-and-one-shot-alerts.md) | complete |
| 2026-09-18 | reference | [LXC resolver and IPv6 behaviour: investigation notes](../../../docs/overview/lxc-dns-ipv6-investigation.md) | complete |
| 2026-09-18 | change | [LXC fleet: resolver, IPv6 and Jellyfin address](../../../docs/writeups/changes/2026-09-18-lxc-resolver-ipv6-jellyfin-ip.md) | complete |
| 2026-09-10 | change | [Correlator grace window calibrated from evidence](../../../docs/writeups/changes/2026-09-10-correlator-grace-window-calibration.md) | complete |
| 2026-09-02 | build | [Wazuh agents on Sentry Gate and the Archivist](../../../docs/writeups/builds/2026-09-02-wazuh-agent-deployment.md) | complete |
| 2026-07-29 | build | [OPNsense base install (Sentry Gate)](../../../docs/build/05-opnsense-base-install.md) | in-progress |
| 2026-07-29 | build | [WAN/LAN split and addressing](../../../docs/build/06-wan-lan-network-split.md) | in-progress |
| 2026-07-29 | build | [Tailscale remote access and rule hardening](../../../docs/build/07-tailscale-remote-access.md) | in-progress |
| 2026-07-29 | build | [DNS hardening (Unbound)](../../../docs/build/08-dns-hardening.md) | in-progress |
| 2026-07-29 | build | [Remote access: Tailscale to an OPNsense firewall](../../../docs/build/2026-07-29-remote-access-tailscale.md) | complete |
| 2026-07-29 | reference | [Network architecture and design decisions](../../../docs/overview/network-architecture.md) | complete |
| 2026-07-28 | incident | [Booting OPNsense on 2008 hardware](../../../docs/build/2026-07-28-opnsense-legacy-bios-boot.md) | complete |
| 2026-07-27 | build | [Build log, July 2026](../../../docs/build/2026-07-27-build-log.md) | complete |
| 2026-07-21 | build | [Initial hardware installation (Arch / Sentry Gate)](../../../docs/build/2026-07-21-initial-hardware.md) | complete |

## Known issues / follow-ups

- [ ] Swap missing since the 2026-11-09 reboot: fstab names `/usr/swap0`, the file is gone. `swapinfo -h` is empty.
- [ ] `netdata` host override in Unbound points at nothing; delete it.
- [ ] A broad tailnet → any pass rule shadows narrower Tailscale rules (0 evaluations on the responder rule).
- [ ] LAN NIC `em0` is 10/100 only (~90 Mbit/s cap); a gigabit PCIe NIC is undecided.
