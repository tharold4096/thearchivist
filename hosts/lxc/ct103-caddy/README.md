---
title: "ct103-caddy — Reverse proxy with an internal CA for every *.home.arpa name"
date: 2026-09-15
type: host
status: running
hosts: [ct103-caddy]
tags: [lxc]
summary: "Reverse proxy with an internal CA for every *.home.arpa name"
verified: 2026-11-12
open: 1
---

# ct103-caddy

> Reverse proxy with an internal CA for every *.home.arpa name.

## At a glance

| | |
|---|---|
| **Role** | Reverse proxy with an internal CA for every *.home.arpa name |
| **Kind** | LXC container (CT 103) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Debian 13 |
| **Address** | 192.168.10.201 |
| **Resources** | 1 core · 512 MiB RAM · 4 GB root |
| **Boot** | starts with the host |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | Checkmk, Wazuh agent 005 |
| **Backed up by** | vzdump → PBS nightly 21:00 |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 22 | tcp | sshd | all | direct |
| 80 | tcp | Caddy HTTP | all | direct |
| 443 | tcp | Caddy HTTPS (tls internal) | all | direct |
| 6556 | tcp | Checkmk agent | all | direct |

## Reverse-proxy routes

| Name | Upstream | Notes |
|---|---|---|
| `jellyfin.home.arpa` | `192.168.10.207:8096` |  |
| `budget.home.arpa` | `192.168.10.206:3000` |  |
| `vaultwarden.home.arpa` | `192.168.10.205:8000` |  |
| `ntfy.home.arpa` | `192.168.10.203:80` | plain HTTP |
| `wazuh.home.arpa` | `192.168.10.204:443` |  |
| `immich.home.arpa` | `192.168.10.208:2283` |  |
| `checkmk.home.arpa` | `192.168.10.215:80` |  |
| `actual.home.arpa` | `192.168.10.206:5006` | Stale: Actual Budget retired, nothing listens on 5006 |

_Media-automation routes are documented locally only._

## Depends on / needed by

- **Needs:** [sentrygate](../../physical/sentrygate/README.md)
- **Needed by:** [ct100-jellyfin](../ct100-jellyfin/README.md), [ct108-immich](../ct108-immich/README.md), [ct200-vaultwarden](../ct200-vaultwarden/README.md), [vm106-budget](../../vm/vm106-budget/README.md)

## Configuration in this repo

_None yet. Anything changed on this host goes here, secrets as `<SET-ON-HOST>`._

## Operating it

```sh
pct status 103                       # on thearchivist
pct exec 103 -- systemctl --failed   # anything broken inside?
pct enter 103                        # shell
pct snapshot 103 pre-change-$(date +%F)   # before you edit anything
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-10-28 | build | [Sure auto-categorization on the responder](../../../docs/writeups/builds/2026-10-28-sure-categorize-responder.md) | complete |
| 2026-10-12 | build | [Checkmk rollout: host, guests, firewall, web UIs, phone alerts](../../../docs/writeups/builds/2026-10-12-checkmk-rollout.md) | complete |
| 2026-10-12 | change | [Netdata removed from the Proxmox host](../../../docs/writeups/changes/2026-10-12-netdata-removal.md) | complete |
| 2026-09-18 | build | [Wazuh agents across the LXC fleet](../../../docs/writeups/builds/2026-09-18-wazuh-lxc-agent-rollout.md) | complete |
| 2026-09-18 | change | [LXC fleet: resolver, IPv6 and Jellyfin address](../../../docs/writeups/changes/2026-09-18-lxc-resolver-ipv6-jellyfin-ip.md) | complete |
| 2026-09-15 | build | [Weekly patch runner: guest coverage, hold gates, thin-pool guard](../../../docs/writeups/builds/2026-09-15-homelab-update-guest-coverage.md) | complete |

## Known issues / follow-ups

- [ ] `actual.home.arpa` route points at 192.168.10.206:5006, where nothing listens (Actual Budget was retired).
