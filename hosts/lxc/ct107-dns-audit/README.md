---
title: "ct107-dns-audit — DNS accountability"
date: 2026-09-15
type: host
status: stopped
hosts: [ct107-dns-audit]
tags: [lxc]
summary: "DNS accountability — attests Sentry's blocking config and reviews DNS logs"
verified: 2026-11-12
open: 1
---

# ct107-dns-audit

> DNS accountability — attests Sentry's blocking config and reviews DNS logs.

## At a glance

| | |
|---|---|
| **Role** | DNS accountability — attests Sentry's blocking config and reviews DNS logs |
| **Kind** | LXC container (CT 107) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | not checked (stopped) |
| **Address** | dhcp |
| **Resources** | 6 cores · 8 GiB RAM · 32 GB root |
| **Mounts** | `/mnt/pve/archive/dnslogs → /srv/dnslogs`<br>`/mnt/pve/bulk2t/models → /srv/models` |
| **Boot** | **manual start** (onboot 0) |
| **Status** | stopped (observed 2026-11-12) |
| **Monitored by** | Wazuh agent 007 |
| **Backed up by** | vzdump → PBS nightly 21:00 |

## Ports

_No listening ports recorded (stopped or client)._

## Depends on / needed by

- **Needs:** [sentrygate](../../physical/sentrygate/README.md), [ct102-ntfy](../ct102-ntfy/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

| File | Deployed to | What it does |
|---|---|---|
| [`attest.diff`](attest.diff) | — | Diff of the YouTube-exemption change |
| [`attest.py`](attest.py) | `/opt/dnsaudit/dnsaudit/attest.py` | Attests Sentry's blocking config against a baseline; one-shot alerts |

## Operating it

```sh
pct status 107                       # on thearchivist
pct exec 107 -- systemctl --failed   # anything broken inside?
pct enter 107                        # shell
pct snapshot 107 pre-change-$(date +%F)   # before you edit anything
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-09-26 | change | [dnsaudit attest: YouTube exemption and one-shot alerts](../../../docs/writeups/changes/2026-09-26-attest-youtube-exemption-and-one-shot-alerts.md) | complete |
| 2026-09-18 | build | [Wazuh agents across the LXC fleet](../../../docs/writeups/builds/2026-09-18-wazuh-lxc-agent-rollout.md) | complete |
| 2026-09-15 | build | [Weekly patch runner: guest coverage, hold gates, thin-pool guard](../../../docs/writeups/builds/2026-09-15-homelab-update-guest-coverage.md) | complete |

## Known issues / follow-ups

- [ ] `onboot: 0`: attestation doesn't run after a power cycle unless started by hand.
