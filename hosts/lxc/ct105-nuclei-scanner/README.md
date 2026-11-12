---
title: "ct105-nuclei-scanner — Vulnerability scanner (Nuclei), run on demand"
date: 2026-11-12
type: host
status: stopped
hosts: [ct105-nuclei-scanner]
tags: [lxc]
summary: "Vulnerability scanner (Nuclei), run on demand"
verified: 2026-11-12
open: 0
---

# ct105-nuclei-scanner

> Vulnerability scanner (Nuclei), run on demand.

## At a glance

| | |
|---|---|
| **Role** | Vulnerability scanner (Nuclei), run on demand |
| **Kind** | LXC container (CT 105) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | not checked (stopped) |
| **Address** | dhcp |
| **Resources** | 2 cores · 2 GiB RAM · 15 GB root |
| **Boot** | **manual start** (onboot 0) |
| **Status** | stopped (observed 2026-11-12) |
| **Monitored by** | **nothing** |
| **Backed up by** | vzdump → PBS nightly 21:00 (when present) |

## Ports

_No listening ports recorded (stopped or client)._

## Depends on / needed by

- **Needs:** [sentrygate](../../physical/sentrygate/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

_None yet. Anything changed on this host goes here, secrets as `<SET-ON-HOST>`._

## Operating it

```sh
pct status 105                       # on thearchivist
pct exec 105 -- systemctl --failed   # anything broken inside?
pct enter 105                        # shell
pct snapshot 105 pre-change-$(date +%F)   # before you edit anything
```

## History

_No writeups yet._

## Known issues / follow-ups

_None open._
