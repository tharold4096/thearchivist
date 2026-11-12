---
title: "vm211-target-juice — Deliberately vulnerable target (OWASP Juice Shop) on the isolated range only"
date: 2026-11-12
type: host
status: stopped
hosts: [vm211-target-juice]
tags: [vm]
summary: "Deliberately vulnerable target (OWASP Juice Shop) on the isolated range only"
verified: 2026-11-12
open: 0
---

# vm211-target-juice

> Deliberately vulnerable target (OWASP Juice Shop) on the isolated range only.

## At a glance

| | |
|---|---|
| **Role** | Deliberately vulnerable target (OWASP Juice Shop) on the isolated range only |
| **Kind** | Virtual machine (VM 211) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Linux |
| **Address** | — |
| **Resources** | 2 cores · 2 GiB RAM · 16 GB root |
| **Boot** | **manual start** (onboot 0) |
| **Status** | stopped (observed 2026-11-12) |
| **Monitored by** | **nothing** |
| **Backed up by** | Excluded from vzdump; LVM snapshot `clean` is the reset point |

## Ports

_No listening ports recorded (stopped or client)._

## Depends on / needed by

- **Needs:** [vm210-range-gw](../vm210-range-gw/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

_None yet. Anything changed on this host goes here, secrets as `<SET-ON-HOST>`._

## Operating it

```sh
qm status 211                                   # on thearchivist
qm guest exec 211 -- systemctl --failed         # needs the guest agent
qm shutdown 211 && qm start 211                 # disk/CPU changes need a full stop/start
```

## History

_No writeups yet._

## Known issues / follow-ups

_None open._
