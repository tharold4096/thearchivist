---
title: "ct116-responder — AI alert responder"
date: 2026-10-13
type: host
status: running
hosts: [ct116-responder]
tags: [lxc]
summary: "AI alert responder — Claude diagnoses Checkmk alerts, one-tap approved fixes; also categorizes Sure transactions"
verified: 2026-11-12
open: 2
---

# ct116-responder

> Turns Checkmk alerts into a Claude diagnosis and a one-tap fix on the phone. Start with [DESIGN.md](DESIGN.md).

## At a glance

| | |
|---|---|
| **Role** | AI alert responder — Claude diagnoses Checkmk alerts, one-tap approved fixes; also categorizes Sure transactions |
| **Kind** | LXC container (CT 116) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Debian 13 |
| **Address** | 192.168.10.216 |
| **Resources** | 2 cores · 2 GiB RAM · 8 GB root |
| **Boot** | starts with the host |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | **nothing** |
| **Backed up by** | vzdump → PBS nightly 21:00; LVM snapshots clean-base … pre-phase3 |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 22 | tcp | sshd | all | direct |
| 8787 | tcp | Responder approval API | 192.168.10.216 | tailscale |

## Depends on / needed by

- **Needs:** [ct115-checkmk](../ct115-checkmk/README.md), [ct102-ntfy](../ct102-ntfy/README.md), [sentrygate](../../physical/sentrygate/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

| File | Deployed to | What it does |
|---|---|---|
| [`DESIGN.md`](DESIGN.md) | — | Trust boundary, approval flow, learned approvals: read this first |
| [`app.py`](app.py) | `/opt/responder/` | HTTP service: `/alert` intake and approval endpoints |
| [`bin/`](bin/) | `/usr/local/bin/` | Runner and read-only gate wrappers |
| [`categorize-prompt.md`](categorize-prompt.md) | — | — |
| [`categorize.py`](categorize.py) | `/opt/responder/` | Sure transaction categorizer |
| [`categorize.schema.json`](categorize.schema.json) | — | — |
| [`deploy/`](deploy/) | systemd, nftables, sudoers, rgate | Everything needed to rebuild CT 116 |
| [`diagnose.py`](diagnose.py) | `/opt/responder/` | Runs the sandboxed Claude diagnosis |
| [`diagnosis.schema.json`](diagnosis.schema.json) | — | — |
| [`executor.py`](executor.py) | `/opt/responder/` | Deterministic action runner + verification |
| [`grants.py`](grants.py) | `/opt/responder/` | Learned approvals with limits and revocation |
| [`journal.py`](journal.py) | — | — |
| [`notify.py`](notify.py) | — | — |
| [`registry.py`](registry.py) | — | — |
| [`registry.toml`](registry.toml) | `/etc/responder/registry.toml` | Allowlist of actions Claude may propose |
| [`store.py`](store.py) | — | — |
| [`system-prompt.md`](system-prompt.md) | — | — |
| [`tests/`](tests/) | — | Unit tests (`python3 -m pytest`) |

## Operating it

```sh
pct status 116                       # on thearchivist
pct exec 116 -- systemctl --failed   # anything broken inside?
pct enter 116                        # shell
pct snapshot 116 pre-change-$(date +%F)   # before you edit anything
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-10-28 | build | [Sure auto-categorization on the responder](../../../docs/writeups/builds/2026-10-28-sure-categorize-responder.md) | complete |
| 2026-10-21 | incident | [samba-vm fwupd-refresh alert flap](../../../docs/writeups/incidents/2026-10-21-samba-vm-fwupd-alert-flap.md) | complete |
| 2026-10-13 | build | [Responder: build, deploy and first live remediation](../../../docs/writeups/builds/2026-10-13-responder-build-and-live-run.md) | complete |
| 2026-10-13 | build | [Responder phase 2: iOS ntfy approval-button spike](../../../docs/writeups/builds/2026-10-13-responder-phase2-ios-approval-spike.md) | complete |

## Known issues / follow-ups

- [ ] No IPv6 drop-in, no Checkmk agent, no Wazuh agent.
- [ ] Flap suppression not built (see the samba-vm fwupd incident).
