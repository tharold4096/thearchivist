---
title: "vm101-samba — Family file server"
date: 2026-09-15
type: host
status: running
hosts: [vm101-samba]
tags: [vm]
summary: "Family file server — four users, 100 GB quota each"
verified: 2026-11-12
open: 2
---

# vm101-samba

> The family's shared drive. Original build notes are kept below.

## At a glance

| | |
|---|---|
| **Role** | Family file server — four users, 100 GB quota each |
| **Kind** | Virtual machine (VM 101) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Debian 13 |
| **Address** | 192.168.10.120 · Tailscale 100.120.180.99 |
| **Resources** | 2 cores · 2 GiB RAM · 16 GB root · 400 GB data disk |
| **Boot** | starts with the host |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | Checkmk, Wazuh agent 003 |
| **Backed up by** | vzdump → PBS nightly 21:00 |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 22 | tcp | sshd | all | direct |
| 139 | tcp | Samba (NetBIOS) | all | direct |
| 445 | tcp | Samba (SMB) | all | tailscale |
| 6556 | tcp | Checkmk agent | all | direct |

## Depends on / needed by

- **Needs:** [sentrygate](../../physical/sentrygate/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

_None yet. Anything changed on this host goes here, secrets as `<SET-ON-HOST>`._

## Operating it

```sh
qm status 101                                   # on thearchivist
qm guest exec 101 -- systemctl --failed         # needs the guest agent
qm shutdown 101 && qm start 101                 # disk/CPU changes need a full stop/start
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-10-21 | incident | [samba-vm fwupd-refresh alert flap](../../../docs/writeups/incidents/2026-10-21-samba-vm-fwupd-alert-flap.md) | complete |
| 2026-10-12 | build | [Checkmk rollout: host, guests, firewall, web UIs, phone alerts](../../../docs/writeups/builds/2026-10-12-checkmk-rollout.md) | complete |
| 2026-09-28 | build | [Thin-pool guard and ntfy delivery fixes](../../../docs/writeups/builds/2026-09-28-thinpool-guard.md) | complete |
| 2026-09-15 | build | [Weekly patch runner: guest coverage, hold gates, thin-pool guard](../../../docs/writeups/builds/2026-09-15-homelab-update-guest-coverage.md) | complete |

## Known issues / follow-ups

- [ ] 192.168.10.120 is inside the DHCP pool (.100–.200).
- [ ] Kernel and OpenEXR Criticals have no Debian fix yet.

## Original notes

Samba file server — progress summary

VM built and fully configured on the Archivist: Debian 13, dedicated 400GB disk (archive:400) separate from Jellyfin's storage, ext4 with usrquota, four accounts (jill, adam, caleb, wesley) each capped at 100GB, Samba shares configured and validated. Confirmed working end-to-end over Tailscale. Destination NAT on Sentry Gate (WAN → VM:445) is correctly configured and confirmed functioning at the packet level — full three-way handshake completes in both directions between the family LAN and the VM.

Blocked on: Client/AP Isolation on the family WiFi router silently drops the return path between same-network WiFi devices — confirmed via packet capture (SYN-ACK sent, never arrives) and a failed same-network ping test. This is a deliberate security posture on the router, not a misconfiguration on Sentry Gate or the VM, and the decision has been made not to disable it network-wide. Resolution requires either per-device isolation exceptions (if the router supports that granularity) or a different access path for family devices — deferred to a later session, not an open bug in the file server itself.

Everything downstream of the router is done and correct. When this gets picked back up, the fix is router-side, not another pass through Samba/NAT/firewall config.
