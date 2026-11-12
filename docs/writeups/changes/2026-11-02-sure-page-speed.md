---
title: "Sure slow pages: 2 Puma workers and 4 cores"
date: 2026-11-02
type: change
status: complete
hosts: [vm106-budget, thearchivist]
tags: [performance, sure, rails, puma]
summary: "Measured first, found Puma single-process CPU was the bottleneck rather than the database, and moved VM 106 to 4 cores with 2 Puma workers."
verified: 2026-11-02
open: 1
---

# Sure (budget VM): slow pages, 2 Puma workers and 4 cores

## At a glance

| | |
|---|---|
| **What** | VM 106 cores 2 → 4; `WEB_CONCURRENCY` unset (1 Puma process) → 2 |
| **Why** | Dashboard and account pages took 2.8–3.4 s cold |
| **Where** | thearchivist · `qm set 106 --cores 4`; vm106-budget · `/opt/sure/compose.override.yml` |
| **Risk** | More RAM per worker (~380 MB) |
| **Rollback** | `qm set 106 --cores 2`; remove the override |
| **Verified** | 2026-11-02: power-cycle check all PASS; `/up` 0.16 s warm |

## Context

* The Sure web UI felt slow: dashboard and account pages often took several seconds.
* I wanted to find the real bottleneck before changing anything, instead of just adding resources.

## What changed

* **Tools/stack:** curl `-w` timings, Rails request logs (`Completed … in Xms (Views | ActiveRecord | GC)`), `docker stats`, `/proc/pressure`, `qm`.
* **Diagnosis (read-only):**
  * `/up` took 70–150 ms through Caddy and also directly on :3000, so the network, DNS, TLS and Caddy weren't the cause.
  * The VM was idle: load 0.1, 2.5 GB RAM free, no swap use, no IO pressure, no errors in the logs.
  * Slow requests were clustered at the start of a session: `/` took 2.8 s, and two account pages plus a transactions page that loaded at the same moment took 2.8–3.4 s each. A minute later the same pages took 250–900 ms.
  * Once warm, database time on account pages was about 40 ms. The rest is view rendering (about 700 ms) plus GC pauses of up to 460 ms. That's CPU-bound work on a 2010 Xeon E5645.
  * `WEB_CONCURRENCY` was unset, so Puma ran one process with 3 threads. Parallel requests (sparklines, turbo frames) queued on a single GVL, with only 2 vCPUs.
  * YJIT was already enabled (Ruby 3.4.9, Rails 8.1), so there was no free win there.
* **Key steps:**
  * Confirmed that Sure's `config/puma.rb` reads `WEB_CONCURRENCY` (`workers` + `preload_app!` in production) and that the DB pool is per-process (`RAILS_MAX_THREADS`, 3). So 2 workers use 6 web connections.
  * Added `WEB_CONCURRENCY: "2"` to `web` only in `/opt/sure/compose.override.yml` (backup: `compose.override.yml.bak-20261102`). Validated with `docker compose --profile backup config`: web=2, worker unset, backup mounts unchanged.
  * On the host: `qm config 106` saved to `/root/qm-106.conf.bak-20261102`, then `qm set 106 --cores 4`, then a cold `qm shutdown` / `qm start` (a change to `cores` needs a full stop and start). Sidekiq was checked idle first (busy=0, enqueued=0).
  * `docker compose up -d web` to recreate the container with the new env.
* **Config/scripts:** [`hosts/vm/vm106-budget/compose.override.yml`](../../../hosts/vm/vm106-budget/compose.override.yml), [`hosts/vm/vm106-budget/sure-runbook.md`](../../../hosts/vm/vm106-budget/sure-runbook.md)

## Issues hit

* **Issue: the planned `.env` change would have done nothing**
  Symptom: none; caught before applying it.
  Root cause: Sure's `compose.yml` has no `env_file`. Containers only get the variables listed in the `x-rails-env` anchor, and `WEB_CONCURRENCY` isn't one of them.
  Fix: set it in `compose.override.yml` under `web.environment`, which merges with the anchor.
* **Issue: after the VM restart, web still ran in single mode**
  Symptom: `WEB_CONCURRENCY=` was empty in the container, and there were no `cluster worker` processes.
  Root cause: on boot, Docker restarts existing containers (`restart: unless-stopped`) with the config they were created with. The compose override only applies when a container is created.
  Fix: `docker compose up -d web`. Noted in the runbook: after any compose change, recreate the service; don't rely on a reboot.

## Verification

* `nproc` = 4 in the guest; `Puma starting in cluster mode… Workers: 2`; two `puma: cluster worker` processes; web at 382 MB right after boot (2.2 GB still free).
* `sure-powercycle-check.sh`: all PASS. That covers a clean poweroff, all 5 services back up, the backup disk mounted, the latest scheduled backup 1 h old with checksums OK, and HTTPS 302 over trusted TLS.
* `/up` went from ~0.35 s just after boot to ~0.16 s once warm.
* Still to do: compare the `Completed … in Xms` times for `/` and `/accounts/*` with the 2026-11-02 baseline (cold 2.8–3.4 s, warm 0.4–1.0 s) after a few days of use.

## Follow-ups

Status as of 2026-11-12. Ticked items are closed; the evidence is in *Current state* above or the linked doc.

- [ ] Compare `Completed … in Xms` for `/` and `/accounts/*` against the 2026-11-02 baseline (cold 2.8–3.4 s, warm 0.4–1.0 s).

## Lessons

* Measure before buying resources. The database was never the bottleneck, so a tuning pass on Postgres would have been wasted effort.
* The remaining limit is single-core speed on the R710. Any page still takes ~0.5 s just to render, and only newer hardware changes that.

---

## Resume line

* Diagnosed slow page loads in a self-hosted Rails finance app by breaking request time into view rendering, database time and GC. Ruled out the network, proxy and database, and traced the slowness to GVL queueing on a single Puma process. Fixed it with 2 Puma workers and 4 vCPUs, verified by a scripted power-cycle check.
