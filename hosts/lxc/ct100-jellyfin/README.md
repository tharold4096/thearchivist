---
title: "ct100-jellyfin — Media server (movies and TV) for the family"
date: 2026-09-15
type: host
status: running
hosts: [ct100-jellyfin]
tags: [lxc]
summary: "Media server (movies and TV) for the family"
verified: 2026-11-12
open: 0
---

# ct100-jellyfin

> Media server (movies and TV) for the family.

## At a glance

| | |
|---|---|
| **Role** | Media server (movies and TV) for the family |
| **Kind** | LXC container (CT 100) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Ubuntu 24.04.5 LTS |
| **Address** | 192.168.10.207 |
| **Resources** | 12 cores · 6 GiB RAM · 16 GB root |
| **Mounts** | `/mnt/pve/bulk2t/data/media → /media` |
| **Web UI** | <https://jellyfin.home.arpa> |
| **Boot** | starts with the host |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | Checkmk, Wazuh agent 014 |
| **Backed up by** | vzdump → PBS nightly 21:00 (media on bulk2t not backed up) |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 22 | tcp | sshd | all | direct |
| 6556 | tcp | Checkmk agent | all | direct |
| 8096 | tcp | Jellyfin | all | caddy |

## Depends on / needed by

- **Needs:** [ct103-caddy](../ct103-caddy/README.md), [sentrygate](../../physical/sentrygate/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

_None yet. Anything changed on this host goes here, secrets as `<SET-ON-HOST>`._

## Operating it

```sh
pct status 100                       # on thearchivist
pct exec 100 -- systemctl --failed   # anything broken inside?
pct enter 100                        # shell
pct snapshot 100 pre-change-$(date +%F)   # before you edit anything
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-10-13 | build | [Responder: build, deploy and first live remediation](../../../docs/writeups/builds/2026-10-13-responder-build-and-live-run.md) | complete |
| 2026-09-18 | build | [Wazuh agents across the LXC fleet](../../../docs/writeups/builds/2026-09-18-wazuh-lxc-agent-rollout.md) | complete |
| 2026-09-18 | change | [LXC fleet: resolver, IPv6 and Jellyfin address](../../../docs/writeups/changes/2026-09-18-lxc-resolver-ipv6-jellyfin-ip.md) | complete |
| 2026-09-15 | build | [Weekly patch runner: guest coverage, hold gates, thin-pool guard](../../../docs/writeups/builds/2026-09-15-homelab-update-guest-coverage.md) | complete |

## Known issues / follow-ups

_None open._
