---
title: "ct104-wazuh — SIEM"
date: 2026-09-02
type: host
status: running
hosts: [ct104-wazuh]
tags: [lxc]
summary: "SIEM — Wazuh manager, indexer and dashboard"
verified: 2026-11-12
open: 1
---

# ct104-wazuh

> SIEM — Wazuh manager, indexer and dashboard.

## At a glance

| | |
|---|---|
| **Role** | SIEM — Wazuh manager, indexer and dashboard |
| **Kind** | LXC container (CT 104) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Debian 13 |
| **Address** | 192.168.10.204 |
| **Resources** | 4 cores · 16 GiB RAM · 64 GB root |
| **Web UI** | <https://wazuh.home.arpa> |
| **Boot** | starts with the host |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | Checkmk, Wazuh agent 000 (manager) |
| **Backed up by** | vzdump → PBS nightly 21:00 |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 22 | tcp | sshd | all | direct |
| 443 | tcp | Wazuh dashboard | all | caddy |
| 1514 | tcp | wazuh-remoted (agent events) | all | direct |
| 1515 | tcp | wazuh-authd (enrollment, password) | all | direct |
| 6556 | tcp | Checkmk agent | all | direct |
| 55000 | tcp | Wazuh API | all | direct |

## Depends on / needed by

- **Needs:** [sentrygate](../../physical/sentrygate/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

| File | Deployed to | What it does |
|---|---|---|
| [`local_rules.xml`](local_rules.xml) | `/var/ossec/etc/rules/local_rules.xml` | Child rules that un-silence pfSense/OPNsense block alerts, DNSBL decoding |
| [`lxc-agents/`](lxc-agents/) | run from the host | `wz-enroll.sh`: enroll an LXC as a pinned agent |
| [`retention/`](retention/) | indexer ISM policy + cron | 90-day index retention |

## Operating it

```sh
pct status 104                       # on thearchivist
pct exec 104 -- systemctl --failed   # anything broken inside?
pct enter 104                        # shell
pct snapshot 104 pre-change-$(date +%F)   # before you edit anything
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-09-18 | build | [Wazuh agents across the LXC fleet](../../../docs/writeups/builds/2026-09-18-wazuh-lxc-agent-rollout.md) | complete |
| 2026-09-15 | build | [Weekly patch runner: guest coverage, hold gates, thin-pool guard](../../../docs/writeups/builds/2026-09-15-homelab-update-guest-coverage.md) | complete |
| 2026-09-02 | build | [Wazuh agents on Sentry Gate and the Archivist](../../../docs/writeups/builds/2026-09-02-wazuh-agent-deployment.md) | complete |

## Known issues / follow-ups

- [ ] Agent 015 `actualbudget` is stale; CT 115, CT 116, VM 106 and VM 150 have no agent.
