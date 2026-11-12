---
title: <slug> — <one-line role>
date: YYYY-MM-DD            # when this host was first built
type: host
status: running             # running | stopped | planned | retired
hosts: [<slug>]
tags: []
summary: >-
  What this machine is for, in one sentence.
verified: YYYY-MM-DD
open: 0
---

# <slug>

> One or two sentences: what this host does in the lab and what breaks if it is down.

## At a glance

| | |
|---|---|
| **Kind** | Physical / LXC / VM / Client |
| **Runs on** | thearchivist (Proxmox CT/VM <id>) |
| **OS** | Debian 13 |
| **Address** | 192.168.10.x/24, gateway 192.168.10.1 |
| **Resources** | n cores · n GiB RAM · n GiB disk (storage) |
| **Web UI** | `https://<name>.home.arpa` via Caddy, or `http://ip:port` |
| **Boot** | onboot yes/no |
| **Monitored by** | Checkmk agent · Wazuh agent `<id>` |
| **Backed up by** | vzdump → PBS nightly 21:00 / none (why) |

## Ports

| Port | Proto | Service | Bound to | Reachable from |
|---|---|---|---|---|
| 22 | tcp | sshd | all | LAN |

## Depends on / depended on by

- **Needs:** sentrygate (DNS, gateway), …
- **Needed by:** …

## Configuration in this repo

| File | Deployed to | What it does |
|---|---|---|
| [`file`](file) | `/etc/...` | … |

## Operating it

The handful of commands you actually use: status, logs, restart, the health check.

```sh
pct exec <id> -- systemctl status <svc>
```

## History

| Date | Type | Writeup |
|---|---|---|
| YYYY-MM-DD | build | [title](../../../docs/writeups/builds/…) |

## Known issues / follow-ups

- [ ] Open item, and the command that would close it.
