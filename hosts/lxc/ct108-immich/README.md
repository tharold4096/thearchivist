---
title: "ct108-immich — Family photo library (Immich)"
date: 2026-09-18
type: host
status: running
hosts: [ct108-immich]
tags: [lxc]
summary: "Family photo library (Immich)"
verified: 2026-11-12
open: 0
---

# ct108-immich

> Family photo library (Immich).

## At a glance

| | |
|---|---|
| **Role** | Family photo library (Immich) |
| **Kind** | LXC container (CT 108) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Debian 13 |
| **Address** | 192.168.10.208 |
| **Resources** | 8 cores · 8 GiB RAM · 32 GB root |
| **Mounts** | `/mnt/pve/archive/immich → /mnt/immich` |
| **Web UI** | <https://immich.home.arpa> |
| **Boot** | starts with the host |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | Checkmk, Wazuh agent 016 |
| **Backed up by** | vzdump → PBS nightly 21:00; library via pbs-precious (file-level, 21:45) |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 22 | tcp | sshd | all | direct |
| 2283 | tcp | Immich API + web | all | caddy |
| 3003 | tcp | Immich machine learning | all | direct |
| 6556 | tcp | Checkmk agent | all | direct |

## Depends on / needed by

- **Needs:** [ct103-caddy](../ct103-caddy/README.md), [sentrygate](../../physical/sentrygate/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

_None yet. Anything changed on this host goes here, secrets as `<SET-ON-HOST>`._

## Operating it

```sh
pct status 108                       # on thearchivist
pct exec 108 -- systemctl --failed   # anything broken inside?
pct enter 108                        # shell
pct snapshot 108 pre-change-$(date +%F)   # before you edit anything
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-09-18 | build | [Wazuh agents across the LXC fleet](../../../docs/writeups/builds/2026-09-18-wazuh-lxc-agent-rollout.md) | complete |

## Known issues / follow-ups

_None open._
