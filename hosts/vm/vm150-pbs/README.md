---
title: "vm150-pbs — Proxmox Backup Server"
date: 2026-09-28
type: host
status: running
hosts: [vm150-pbs]
tags: [vm]
summary: "Proxmox Backup Server — datastore store1 on a passed-through 2 TB disk"
verified: 2026-11-12
open: 1
---

# vm150-pbs

> Proxmox Backup Server — datastore store1 on a passed-through 2 TB disk.

## At a glance

| | |
|---|---|
| **Role** | Proxmox Backup Server — datastore store1 on a passed-through 2 TB disk |
| **Kind** | Virtual machine (VM 150) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Debian 13 (Proxmox Backup Server) |
| **Address** | 192.168.10.220 |
| **Resources** | 2 cores · 4 GiB RAM · 32 GB root · 1862 GB data disk |
| **Web UI** | <https://192.168.10.220:8007> |
| **Boot** | starts with the host |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | Checkmk |
| **Backed up by** | Excluded from vzdump (it is the backup target) |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 22 | tcp | sshd | all | direct |
| 6556 | tcp | Checkmk agent | all | direct |
| 8007 | tcp | PBS web UI / API | all | direct |

## Depends on / needed by

- **Needs:** [sentrygate](../../physical/sentrygate/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

_None yet. Anything changed on this host goes here, secrets as `<SET-ON-HOST>`._

## Operating it

```sh
qm status 150                                   # on thearchivist
qm guest exec 150 -- systemctl --failed         # needs the guest agent
qm shutdown 150 && qm start 150                 # disk/CPU changes need a full stop/start
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-09-28 | build | [Thin-pool guard and ntfy delivery fixes](../../../docs/writeups/builds/2026-09-28-thinpool-guard.md) | complete |

## Known issues / follow-ups

- [ ] SSH host key fails verification from the Archivist; unexplained.
