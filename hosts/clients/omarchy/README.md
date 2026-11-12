---
title: "omarchy — Admin laptop"
date: 2026-09-10
type: host
status: running
hosts: [omarchy]
tags: [client]
summary: "Admin laptop; DNS pinned to Sentry, homelab status bar widget"
verified: 2026-11-12
open: 1
---

# omarchy

> Admin laptop; DNS pinned to Sentry, homelab status bar widget.

## At a glance

| | |
|---|---|
| **Role** | Admin laptop; DNS pinned to Sentry, homelab status bar widget |
| **Kind** | Client device |
| **OS** | Omarchy (Arch Linux) |
| **Address** | — · Tailscale 100.113.94.88 |
| **Resources** | — |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | **nothing** |
| **Backed up by** | — |

## Ports

_No listening ports recorded (stopped or client)._

## Depends on / needed by

- **Needs:** [sentrygate](../../physical/sentrygate/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

| File | Deployed to | What it does |
|---|---|---|
| [`dns-guard/`](dns-guard/) | `/etc/...`, `/usr/local/bin/sentry-dns-guard` | DNS pinned to Sentry, nftables lock, bypass-detecting guard, pacman hooks |
| [`homelab-status-plugin/`](homelab-status-plugin/) | `~/.config/omarchy/plugins/` | Bar widget: probes ten lab services over Tailscale |

## Operating it

_Client machine; see the config folders below._

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-11-11 | build | [Omarchy shell plugin: Homelab Status](../../../docs/writeups/builds/2026-11-11-omarchy-homelab-status-plugin.md) | complete |
| 2026-10-19 | change | [sentry-dns-guard: package-rewrite windows](../../../docs/writeups/changes/2026-10-19-omarchy-dns-guard-package-rewrites.md) | complete |
| 2026-10-15 | change | [Sentry DNSBL allowlist for the CSCE 3550 gradebot](../../../docs/writeups/changes/2026-10-15-sentrygate-allowlist-gradebot.md) | complete |
| 2026-09-26 | build | [Omarchy DNS lock and sentry-dns-guard](../../../docs/writeups/builds/2026-09-26-omarchy-dns-guard.md) | complete |
| 2026-09-10 | change | [Correlator grace window calibrated from evidence](../../../docs/writeups/changes/2026-09-10-correlator-grace-window-calibration.md) | complete |

## Known issues / follow-ups

- [ ] DNS guard re-logs `txn_untrusted` every poll for stale windows (56 MB events.jsonl).
