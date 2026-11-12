---
title: "ct115-checkmk — Monitoring"
date: 2026-10-12
type: host
status: running
hosts: [ct115-checkmk]
tags: [lxc]
summary: "Monitoring — Checkmk Community, 17 hosts, alerts to ntfy and the responder"
verified: 2026-11-12
open: 3
---

# ct115-checkmk

> Monitoring — Checkmk Community, 17 hosts, alerts to ntfy and the responder.

## At a glance

| | |
|---|---|
| **Role** | Monitoring — Checkmk Community, 17 hosts, alerts to ntfy and the responder |
| **Kind** | LXC container (CT 115) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Debian 13 |
| **Address** | 192.168.10.215 |
| **Resources** | 2 cores · 4 GiB RAM · 16 GB root |
| **Web UI** | <https://checkmk.home.arpa> |
| **Boot** | starts with the host |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | Checkmk |
| **Backed up by** | vzdump → PBS nightly 21:00 |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 22 | tcp | sshd | all | direct |
| 80 | tcp | Checkmk web (Apache) | all | caddy |
| 111 | tcp | rpcbind | all | direct |
| 6556 | tcp | Checkmk agent | all | direct |
| 8000 | tcp | Checkmk agent receiver | all | direct |

## Depends on / needed by

- **Needs:** [sentrygate](../../physical/sentrygate/README.md), [ct102-ntfy](../ct102-ntfy/README.md)
- **Needed by:** [ct116-responder](../ct116-responder/README.md)

## Configuration in this repo

| File | Deployed to | What it does |
|---|---|---|
| [`caddy-checkmk.caddyfile`](caddy-checkmk.caddyfile) | Caddy CT 103 | Route for checkmk.home.arpa |
| [`ntfy-notify.py`](ntfy-notify.py) | `~/local/share/check_mk/notifications/` | Checkmk → ntfy notification plugin |
| [`responder-notify.py`](responder-notify.py) | `~/local/share/check_mk/notifications/` | Checkmk → responder `/alert` plugin |
| [`wato-rules-export.mk.txt`](wato-rules-export.mk.txt) | — | Export of the WATO rules, for rebuilds |

## Operating it

```sh
pct status 115                       # on thearchivist
pct exec 115 -- systemctl --failed   # anything broken inside?
pct enter 115                        # shell
pct snapshot 115 pre-change-$(date +%F)   # before you edit anything
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-10-21 | incident | [samba-vm fwupd-refresh alert flap](../../../docs/writeups/incidents/2026-10-21-samba-vm-fwupd-alert-flap.md) | complete |
| 2026-10-13 | build | [Responder: build, deploy and first live remediation](../../../docs/writeups/builds/2026-10-13-responder-build-and-live-run.md) | complete |
| 2026-10-12 | build | [Checkmk rollout: host, guests, firewall, web UIs, phone alerts](../../../docs/writeups/builds/2026-10-12-checkmk-rollout.md) | complete |

## Known issues / follow-ups

- [ ] Not monitored: VM 106 budget, CT 116 responder, CT 107 dns-audit.
- [ ] No IPv6 drop-in (built after the 2026-09-18 fix).
- [ ] `automation-claude` user still present.
