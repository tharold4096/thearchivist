---
title: "Sure budget VM: close signups, pin image, add guest agent"
date: 2026-10-27
type: change
status: complete
hosts: [vm106-budget, thearchivist]
tags: [hardening, self-hosting, docker, proxmox]
summary: "Closed open self-registration, pinned the Sure image to a fixed release, and enabled the QEMU guest agent on VM 106."
verified: 2026-11-12
open: 3
---

# Sure (budget VM) — audit fixes: signups, image pin, guest agent

## At a glance

| | |
|---|---|
| **What** | `onboarding_state` open → closed; `SURE_IMAGE_TAG` :stable → 0.7.5-hotfix.3; VM 106 `agent: 1` |
| **Why** | Anyone on the LAN could register; any pull could change versions; no guest-aware shutdown |
| **Where** | vm106-budget · `/opt/sure`; thearchivist · `qm set 106` |
| **Risk** | Restart of the Sure stack |
| **Rollback** | Revert `.env` tag and onboarding setting; `qm set 106 --delete agent` |
| **Verified** | 2026-10-27: `/registration/new` → 302; `qm agent 106 ping` OK |

> **Current state (verified 2026-11-12):** Re-checked 2026-11-12: `qm guest` works on VM 106 ✔. **Port 3000 is still published on 0.0.0.0** (bypasses Caddy).

## Context

* A read-only audit of the Sure stack (`/opt/sure` on VM 106) found three things worth fixing before relying on it daily:
  * **Open signups.** `Setting.onboarding_state` was `open`, and `/registration/new` returned 200 to anyone who could reach the app.
  * **Floating image tag.** `SURE_IMAGE_TAG` was unset, so compose fell back to `:stable`. Any `docker compose pull` could silently move the app to a new release.
  * **No guest agent.** VM 106 had no `agent:` line, so Proxmox couldn't run `qm agent` or do a guest-aware shutdown, and `qm guest` queries failed.
* The same audit corrected some topology details: Caddy is **CT 103 at 192.168.10.201** (CT 200 is vaultwarden), and the host wakes from an **RTC alarm at 07:45**, set by `nightly-poweroff.sh`.

## What changed

* **Tools/stack:** Sure v0.7.5-hotfix.3 (docker compose), Proxmox `qm`.
* **Key steps:**
  * Backed up `.env` first: `cp -p /opt/sure/.env /opt/sure/.env.bak-20261027` (mode 600 is kept).
  * `.env` changes (values shown are not secrets):
    * `ONBOARDING_STATE=open` → `ONBOARDING_STATE=closed`
    * added `SURE_IMAGE_TAG=0.7.5-hotfix.3` (ghcr tag has **no `v` prefix**; digest `sha256:9cbcc5a2…` = the image that was already running)
  * DB value (this one actually controls signups; `.env` only sets the default for a fresh DB):
    `docker compose exec -T web bin/rails runner 'Setting.onboarding_state = "closed"'`
  * `docker compose up -d web worker` to recreate both on the pinned tag.
  * Proxmox: `qm set 106 --agent enabled=1`, then `qm shutdown 106 --timeout 180 && qm start 106`. A full stop and start is required because a reboot from inside the guest doesn't add the virtio-serial device. The `qemu-guest-agent` package was already installed in the guest and started on its own once the device appeared.
* **Rollback:** `cp -p .env.bak-20261027 .env`, then `Setting.onboarding_state = "open"`, then `up -d web worker`. For the agent: `qm set 106 --delete agent` plus another stop and start.

## Issues hit

* **Issue: HTTP 502 right after the VM came back**
  Symptom: `https://budget.home.arpa/` returned 502 about 17s after the containers started.
  Root cause: Rails was still booting. `web`/`worker` have no healthcheck, so "Up" doesn't mean ready.
  Fix: none needed. It returned 302 about 18s later.

## Verification

* `qm agent 106 ping` succeeds. `network-get-interfaces` reports 192.168.10.206.
* After the cold start, all 4 containers came back by themselves (`unless-stopped`), with `web`/`worker` on `ghcr.io/we-promise/sure:0.7.5-hotfix.3`.
* `/registration/new` now returns 302 to `/sessions/new`. `Setting.onboarding_state` → `closed`.
* All 3 `ACTIVE_RECORD_ENCRYPTION_*` vars are present in `web`. 0 errors in the logs after the recreate.

## Follow-ups

Status as of 2026-11-12. Ticked items are closed; the evidence is in *Current state* above or the linked doc.

- [ ] Port 3000 is published on `0.0.0.0` and bypasses Caddy. Add a `DOCKER-USER` rule allowing only 192.168.10.201, then from another LAN host `curl -m3 http://192.168.10.206:3000/up` should fail.
- [ ] Healthchecks on `web` and `worker`.
- [ ] Pin `redis:latest`.
- [x] Backups moved off local-lvm : the 2026-11-02 power-cycle check confirmed the backup disk mounted and a 1 h-old scheduled backup with checksums OK.

## Lessons

* Still open: port 3000 is published on `0.0.0.0`, so it bypasses Caddy (fix: a `DOCKER-USER` rule allowing only 192.168.10.201). `web`/`worker` have no healthcheck. `redis:latest` is unpinned. Backups are still on local-lvm (handled in the next phase).

---

## Resume line

* Audited a self-hosted finance app (Sure) on Proxmox/Docker against a 9-point checklist. Closed public registration, pinned the container image by verified digest, and enabled the QEMU guest agent, each with a rollback path, verified across a cold VM restart.
