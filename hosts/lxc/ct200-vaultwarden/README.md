---
title: "ct200-vaultwarden — Password manager (Bitwarden-compatible)"
date: 2026-09-15
type: host
status: running
hosts: [ct200-vaultwarden]
tags: [lxc]
summary: "Password manager (Bitwarden-compatible)"
verified: 2026-11-12
open: 0
---

# ct200-vaultwarden

> Password manager (Bitwarden-compatible).

## At a glance

| | |
|---|---|
| **Role** | Password manager (Bitwarden-compatible) |
| **Kind** | LXC container (CT 200) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Debian 13 |
| **Address** | 192.168.10.205 |
| **Resources** | 1 core · 512 MiB RAM · 12 GB root |
| **Web UI** | <https://vaultwarden.home.arpa> |
| **Boot** | starts with the host |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | Checkmk, Wazuh agent 006 |
| **Backed up by** | vzdump → PBS nightly 21:00 |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 6556 | tcp | Checkmk agent | all | direct |
| 8000 | tcp | Vaultwarden | all | caddy |

## Depends on / needed by

- **Needs:** [ct103-caddy](../ct103-caddy/README.md), [sentrygate](../../physical/sentrygate/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

_None yet. Anything changed on this host goes here, secrets as `<SET-ON-HOST>`._

## Operating it

```sh
pct status 200                       # on thearchivist
pct exec 200 -- systemctl --failed   # anything broken inside?
pct enter 200                        # shell
pct snapshot 200 pre-change-$(date +%F)   # before you edit anything
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-09-18 | build | [Wazuh agents across the LXC fleet](../../../docs/writeups/builds/2026-09-18-wazuh-lxc-agent-rollout.md) | complete |
| 2026-09-15 | build | [Weekly patch runner: guest coverage, hold gates, thin-pool guard](../../../docs/writeups/builds/2026-09-15-homelab-update-guest-coverage.md) | complete |

## Known issues / follow-ups

_None open._
