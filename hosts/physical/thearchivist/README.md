---
title: "thearchivist — Proxmox VE hypervisor running every lab service"
date: 2026-07-29
type: host
status: running
hosts: [thearchivist]
tags: [physical]
summary: "Proxmox VE hypervisor running every lab service"
verified: 2026-11-12
open: 3
---

# thearchivist

> The R710 that runs every service in the lab as Proxmox containers and VMs. It powers off 23:00–07:45 every night, so anything here must survive a daily cold boot.

## At a glance

| | |
|---|---|
| **Role** | Proxmox VE hypervisor running every lab service |
| **Kind** | Physical machine |
| **OS** | Proxmox VE 9.2.26 (kernel 7.0.14-28-pve) |
| **Address** | 192.168.10.202/24 (vmbr0), 192.168.10.245 (idrac) |
| **Resources** | Dell PowerEdge R710, 24 threads (2x Xeon E5645), 94 GiB RAM, PERC 6/i |
| **Web UI** | <https://192.168.10.202:8006> |
| **Schedule** | Powers off 23:00, RTC wake 07:45 (nightly-poweroff cron) |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | Checkmk, Wazuh agent 002 |
| **Backed up by** | Host config not backed up by PBS; configs live in this repo |

## Interfaces

| Name | Role | Address | Notes |
|---|---|---|---|
| `vmbr0` | LAN bridge (nic0) | 192.168.10.202/24 |  |
| `vmbr1` | Isolated range bridge | — |  |
| `idrac` | Out-of-band management | 192.168.10.245 | Not answering on 443 at 2026-11-12 check |

## Storage

| Proxmox storage | Type | Device | Used for |
|---|---|---|---|
| `local` | dir | sda (232 GB, PERC VD) | ISOs, templates, host root |
| `local-lvm` | lvmthin | sda | Guest root disks (60% full, 2.35x overprovisioned) |
| `archive` | dir | sdb (931 GB) | Immich library, Takeout, DNS logs, samba share, budget backups |
| `bulk2t` | dir | sdc (1.8 TB) | Media library and torrents (/data) |
| `pbs` | pbs | sdd (1.8 TB, passed through to VM 150) | vzdump + file-level backups |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 22 | tcp | sshd | all | direct |
| 111 | tcp | rpcbind | all | direct |
| 3128 | tcp | spiceproxy | all | direct |
| 6556 | tcp | Checkmk agent | all | direct |
| 8006 | tcp | Proxmox web UI / API | all | direct |

## Guests

[ct100-jellyfin](../../lxc/ct100-jellyfin/README.md), [ct102-ntfy](../../lxc/ct102-ntfy/README.md), [ct103-caddy](../../lxc/ct103-caddy/README.md), [ct104-wazuh](../../lxc/ct104-wazuh/README.md), [ct105-nuclei-scanner](../../lxc/ct105-nuclei-scanner/README.md), [ct107-dns-audit](../../lxc/ct107-dns-audit/README.md), [ct108-immich](../../lxc/ct108-immich/README.md), [ct115-checkmk](../../lxc/ct115-checkmk/README.md), [ct116-responder](../../lxc/ct116-responder/README.md), [ct200-vaultwarden](../../lxc/ct200-vaultwarden/README.md), [vm101-samba](../../vm/vm101-samba/README.md), [vm106-budget](../../vm/vm106-budget/README.md), [vm150-pbs](../../vm/vm150-pbs/README.md), [vm210-range-gw](../../vm/vm210-range-gw/README.md), [vm211-target-juice](../../vm/vm211-target-juice/README.md)

## Depends on / needed by

- **Needs:** [sentrygate](../sentrygate/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

| File | Deployed to | What it does |
|---|---|---|
| [`fan-watchdog/`](fan-watchdog/) | `/usr/local/bin/fan-watchdog.sh`, `fan-watchdog.service` | Quiet manual fan speed via IPMI; hands control back to the BMC at 75 °C or on any bad reading |
| [`hardware.md`](hardware.md) | — | R710 hardware baseline as acquired |
| [`homelab-update/`](homelab-update/) | `/usr/local/sbin/homelab-update` + systemd units | Sunday 08:15 patch runner for host, LXCs and samba-vm, with snapshots and hold gates |
| [`lxc-dns-ipv6/`](lxc-dns-ipv6/) | each CT's `/etc/sysctl.d/99-no-ipv6-eth0.conf` | Disables IPv6 on container eth0 (AAAA blackhole fix) |
| [`nightly-poweroff/`](nightly-poweroff/) | `/etc/cron.d/archivist-nightly-off`, `/usr/local/sbin/nightly-poweroff.sh` | 22:55 shutdown with a 07:45 RTC wake alarm |
| [`ossec-additions.xml`](ossec-additions.xml) | `/var/ossec/etc/ossec.conf` (merged) | Host Wazuh agent additions |
| [`pbs-precious/`](pbs-precious/) | `/etc/systemd/system/pbs-precious.{service,timer}` | 21:45 file-level PBS backup of Immich, Takeout and DNS logs from the archive disk |
| [`responder-stop-first.service`](responder-stop-first.service) | **not deployed** | Stops CT 116 before other guests on shutdown so the responder doesn't page about its own host going down |
| [`thinpool-guard/`](thinpool-guard/) | `/usr/local/sbin/thinpool-alert` + timer, `/etc/thinpool-alert.conf` | 15-minute LVM-thin fill alert to ntfy |

## Operating it

```sh
pct list; qm list                     # what's running
lvs pve/data                          # thin-pool fill (alert at 70/85%)
systemctl list-timers homelab-update thinpool-alert pbs-precious
journalctl -t nightly-poweroff -b -1  # last night's wake alarm
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-11-02 | change | [Sure slow pages: 2 Puma workers and 4 cores](../../../docs/writeups/changes/2026-11-02-sure-page-speed.md) | complete |
| 2026-10-27 | change | [Sure budget VM: close signups, pin image, add guest agent](../../../docs/writeups/changes/2026-10-27-sure-audit-hardening.md) | complete |
| 2026-10-13 | change | [Nightly poweroff: re-enable](../../../docs/writeups/changes/2026-10-13-nightly-poweroff-reenable.md) | complete |
| 2026-10-13 | change | [ntfy: every publisher onto the alerts topic](../../../docs/writeups/changes/2026-10-13-ntfy-topic-consolidation.md) | complete |
| 2026-10-12 | build | [Checkmk rollout: host, guests, firewall, web UIs, phone alerts](../../../docs/writeups/builds/2026-10-12-checkmk-rollout.md) | complete |
| 2026-10-12 | change | [Netdata removed from the Proxmox host](../../../docs/writeups/changes/2026-10-12-netdata-removal.md) | complete |
| 2026-09-28 | build | [Thin-pool guard and ntfy delivery fixes](../../../docs/writeups/builds/2026-09-28-thinpool-guard.md) | complete |
| 2026-09-24 | change | [Nightly poweroff: disable](../../../docs/writeups/changes/2026-09-24-nightly-poweroff-disable.md) | complete |
| 2026-09-23 | change | [Nightly poweroff: re-enable and manual post-midnight shutdown](../../../docs/writeups/changes/2026-09-23-nightly-poweroff-reenable.md) | complete |
| 2026-09-18 | reference | [LXC resolver and IPv6 behaviour: investigation notes](../../../docs/overview/lxc-dns-ipv6-investigation.md) | complete |
| 2026-09-18 | build | [Wazuh agents across the LXC fleet](../../../docs/writeups/builds/2026-09-18-wazuh-lxc-agent-rollout.md) | complete |
| 2026-09-18 | change | [LXC fleet: resolver, IPv6 and Jellyfin address](../../../docs/writeups/changes/2026-09-18-lxc-resolver-ipv6-jellyfin-ip.md) | complete |
| 2026-09-17 | change | [Nightly poweroff: skip one night](../../../docs/writeups/changes/2026-09-17-nightly-poweroff-one-night-skip.md) | complete |
| 2026-09-15 | build | [Weekly patch runner: guest coverage, hold gates, thin-pool guard](../../../docs/writeups/builds/2026-09-15-homelab-update-guest-coverage.md) | complete |
| 2026-09-02 | build | [Wazuh agents on Sentry Gate and the Archivist](../../../docs/writeups/builds/2026-09-02-wazuh-agent-deployment.md) | complete |
| 2026-07-29 | build | [BIOS firmware update (R710)](../../../docs/build/01-bios-firmware-update.md) | in-progress |
| 2026-07-29 | build | [iDRAC6 configuration](../../../docs/build/02-idrac-configuration.md) | in-progress |
| 2026-07-29 | build | [RAID and storage (PERC 6/i)](../../../docs/build/03-raid-storage-configuration.md) | in-progress |
| 2026-07-29 | build | [Memory population and power tuning](../../../docs/build/04-ram-power-tuning.md) | in-progress |
| 2026-07-29 | build | [Proxmox VE installation](../../../docs/build/09-proxmox-installation.md) | in-progress |
| 2026-07-29 | reference | [Network architecture and design decisions](../../../docs/overview/network-architecture.md) | complete |

## Known issues / follow-ups

- [ ] `responder-stop-first.service` and the trim-every-CT change (commit 1ed7057) are in the repo but **not deployed**.
- [ ] `nightly-poweroff.sh` still uses `tomorrow 07:45`; never run it by hand after midnight.
- [ ] iDRAC (192.168.10.245) did not answer on 443 at the 2026-11-12 check.
