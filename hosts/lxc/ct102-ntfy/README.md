---
title: "ct102-ntfy — Push-notification server"
date: 2026-09-15
type: host
status: running
hosts: [ct102-ntfy]
tags: [lxc]
summary: "Push-notification server; every alert in the lab ends here"
verified: 2026-11-12
open: 0
---

# ct102-ntfy

> Push-notification server; every alert in the lab ends here.

## At a glance

| | |
|---|---|
| **Role** | Push-notification server; every alert in the lab ends here |
| **Kind** | LXC container (CT 102) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Debian 13 |
| **Address** | 192.168.10.203 |
| **Resources** | 1 core · 512 MiB RAM · 2 GB root |
| **Web UI** | <http://ntfy.home.arpa> |
| **Boot** | starts with the host |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | Checkmk, Wazuh agent 004 |
| **Backed up by** | vzdump → PBS nightly 21:00 |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 22 | tcp | sshd | all | direct |
| 80 | tcp | ntfy | all | caddy |
| 6556 | tcp | Checkmk agent | all | direct |

## Depends on / needed by

- **Needs:** [sentrygate](../../physical/sentrygate/README.md)
- **Needed by:** [ct107-dns-audit](../ct107-dns-audit/README.md), [ct115-checkmk](../ct115-checkmk/README.md), [ct116-responder](../ct116-responder/README.md)

## Configuration in this repo

| File | Deployed to | What it does |
|---|---|---|
| [`ntfy-acl.md`](ntfy-acl.md) | ntfy user DB | Users, ACLs and why topic names stay off git |
| [`ntfy-server.yml.diff`](ntfy-server.yml.diff) | `/etc/ntfy/server.yml` | base-url fix and on-disk message cache |

## Operating it

```sh
pct status 102                       # on thearchivist
pct exec 102 -- systemctl --failed   # anything broken inside?
pct enter 102                        # shell
pct snapshot 102 pre-change-$(date +%F)   # before you edit anything
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-10-13 | build | [Responder: build, deploy and first live remediation](../../../docs/writeups/builds/2026-10-13-responder-build-and-live-run.md) | complete |
| 2026-10-13 | build | [Responder phase 2: iOS ntfy approval-button spike](../../../docs/writeups/builds/2026-10-13-responder-phase2-ios-approval-spike.md) | complete |
| 2026-10-13 | change | [ntfy: every publisher onto the alerts topic](../../../docs/writeups/changes/2026-10-13-ntfy-topic-consolidation.md) | complete |
| 2026-10-12 | build | [Checkmk rollout: host, guests, firewall, web UIs, phone alerts](../../../docs/writeups/builds/2026-10-12-checkmk-rollout.md) | complete |
| 2026-09-28 | build | [Thin-pool guard and ntfy delivery fixes](../../../docs/writeups/builds/2026-09-28-thinpool-guard.md) | complete |
| 2026-09-18 | build | [Wazuh agents across the LXC fleet](../../../docs/writeups/builds/2026-09-18-wazuh-lxc-agent-rollout.md) | complete |
| 2026-09-15 | build | [Weekly patch runner: guest coverage, hold gates, thin-pool guard](../../../docs/writeups/builds/2026-09-15-homelab-update-guest-coverage.md) | complete |

## Known issues / follow-ups

_None open._
