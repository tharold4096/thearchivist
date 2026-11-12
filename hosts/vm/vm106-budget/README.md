---
title: "vm106-budget — Personal finance"
date: 2026-09-24
type: host
status: running
hosts: [vm106-budget]
tags: [vm]
summary: "Personal finance — Sure (Rails) in Docker, SimpleFIN sync"
verified: 2026-11-12
open: 3
---

# vm106-budget

> Personal finance — Sure (Rails) in Docker, SimpleFIN sync.

## At a glance

| | |
|---|---|
| **Role** | Personal finance — Sure (Rails) in Docker, SimpleFIN sync |
| **Kind** | Virtual machine (VM 106) |
| **Runs on** | [thearchivist](../../physical/thearchivist/README.md) |
| **OS** | Debian 13 |
| **Address** | 192.168.10.206 |
| **Resources** | 4 cores · 4 GiB RAM · 32 GB root · 20 GB data disk |
| **Web UI** | <https://budget.home.arpa> |
| **Boot** | starts with the host |
| **Status** | running (observed 2026-11-12) |
| **Monitored by** | Wazuh agent 015 (stale, as actualbudget) |
| **Backed up by** | Sure's own scheduled backup to the archive disk (scsi1); vzdump → PBS nightly 21:00 |

## Ports

| Port | Proto | Service | Bound to | Reached via |
|---|---|---|---|---|
| 22 | tcp | sshd | all | direct |
| 3000 | tcp | Sure web (Puma, 2 workers) — Also published on 0.0.0.0 — bypasses Caddy (open follow-up) | all | caddy |

## Depends on / needed by

- **Needs:** [ct103-caddy](../../lxc/ct103-caddy/README.md), [sentrygate](../../physical/sentrygate/README.md)
- **Needed by:** nothing recorded

## Configuration in this repo

| File | Deployed to | What it does |
|---|---|---|
| [`Caddyfile.budget.fragment`](Caddyfile.budget.fragment) | Caddy CT 103 | Route for budget.home.arpa |
| [`categorize-setup.md`](categorize-setup.md) | — | Setup checklist for the categorizer on CT 116 |
| [`compose.override.yml`](compose.override.yml) | `/opt/sure/compose.override.yml` | Puma workers, backup mounts |
| [`sure-api-check.sh`](sure-api-check.sh) | — | API smoke test |
| [`sure-powercycle-check.sh`](sure-powercycle-check.sh) | — | Post-boot health check |
| [`sure-runbook.md`](sure-runbook.md) | — | Operating Sure: backups, restore, upgrades |
| [`sure-wf-verify.rb`](sure-wf-verify.rb) | — | Wells Fargo import verification (Rails runner) |
| [`sure-wf-verify.sh`](sure-wf-verify.sh) | — | Wells Fargo import verification (wrapper) |

## Operating it

```sh
qm status 106                                   # on thearchivist
qm guest exec 106 -- systemctl --failed         # needs the guest agent
qm shutdown 106 && qm start 106                 # disk/CPU changes need a full stop/start
```

## History

| Date | Type | Writeup | Status |
|---|---|---|---|
| 2026-11-02 | change | [Sure slow pages: 2 Puma workers and 4 cores](../../../docs/writeups/changes/2026-11-02-sure-page-speed.md) | complete |
| 2026-10-28 | build | [Sure auto-categorization on the responder](../../../docs/writeups/builds/2026-10-28-sure-categorize-responder.md) | complete |
| 2026-10-27 | change | [Sure budget VM: close signups, pin image, add guest agent](../../../docs/writeups/changes/2026-10-27-sure-audit-hardening.md) | complete |

## Known issues / follow-ups

- [ ] Port 3000 published on 0.0.0.0 (bypasses Caddy).
- [ ] No `discard` on scsi0; no Checkmk agent; Wazuh entry is the stale 015.
- [ ] `redis:latest` unpinned; no healthchecks on web/worker.
