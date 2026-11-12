---
title: "vm210-range-gw — Attack-range gateway between the lab LAN and the isolated vmbr1"
date: 2026-11-12
type: host
status: stopped
hosts: [vm210-range-gw]
tags: [vm]
summary: "Attack-range gateway between the lab LAN and the isolated vmbr1"
verified: 2026-11-12
open: 0
---

# vm210-range-gw

> Attack-range gateway between the lab LAN and the isolated vmbr1.

## At a glance

| | |
|---|---|
| **Role** | Attack-range gateway between the lab LAN and the isolated vmbr1 |
| **Kind** | Virtual machine (VM 210) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Linux |
| **Address** | — |
| **Resources** | 1 core · 512 MiB RAM · 8 GB root |
| **Boot** | **manual start** (onboot 0) |
| **Status** | stopped (observed 2026-11-12) |
| **Monitored by** | **nothing** |
| **Backed up by** | Excluded from vzdump |

## Ports

_No listening ports recorded (stopped or client)._

## Depends on / needed by

- **Needs:** nothing in the lab
- **Needed by:** [vm211-target-juice](../vm211-target-juice/README.md)

## Configuration in this repo

_None yet. Anything changed on this host goes here, secrets as `<SET-ON-HOST>`._

## Operating it

```sh
qm status 210                                   # on thearchivist
qm guest exec 210 -- systemctl --failed         # needs the guest agent
qm shutdown 210 && qm start 210                 # disk/CPU changes need a full stop/start
```

## History

_No writeups yet._

## Known issues / follow-ups

_None open._
