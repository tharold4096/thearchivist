---
title: "Thin-pool guard and ntfy delivery fixes"
date: 2026-09-28
type: build
status: complete
hosts: [thearchivist, ct102-ntfy, vm101-samba, vm150-pbs]
tags: [storage, lvm-thin, monitoring, ntfy, hardening]
summary: "Added a 15-minute thin-pool fill alert with one-shot escalation, enabled discard on VM disks so freed space returns to the pool, and fixed ntfy's base-url and RAM-only cache."
verified: 2026-11-12
open: 2
---

# local-lvm thin pool guard + ntfy delivery fixes

## At a glance

| | |
|---|---|
| **Goal** | Warn before `pve/data` fills (when_full = queue hangs every guest at once) |
| **Stack** | bash + systemd timer on the host, ntfy push, VM `discard=on` |
| **Hosts** | thearchivist; VMs 101 and 150; ntfy CT 102 |
| **Entry points** | `thinpool-alert.timer` every 15 min; `THINPOOL_FORCE=1 thinpool-alert` to test |
| **Result** | Pool alert armed with no repeat pushes; space freed in VMs reaches the pool |
| **Config** | hosts/physical/thearchivist/thinpool-guard/ |

> **Current state (verified 2026-11-12):** Open items from this doc, re-checked: `discard=on` is live on VM 101 and VM 150 and `fstrim.timer` is enabled inside PBS ✔; phone delivery confirmed on the alerts topic 2026-10-13 ✔. Still open: VM 106 (budget, added later) has **no** `discard`, and the stale `archive/media` comment in `homelab-update`. Pool at 60.4% today.

## Context

* The `local-lvm` thin pool (`pve/data`) holds every guest root disk. It is **136.5G physical with 321G promised to guests** (~2.35x overprovisioned) and sat at 60.6% data / 3.3% metadata.
* The pool's `when_full` policy is `queue`, so if it fills, writes stall and then fail for **every guest at once**. That is the likely way guest filesystems get corrupted here.
* There is headroom (~54G, plus one ~14G autoextend from the 16G VG free space), but nothing warned before it ran out. The weekly `pct fstrim` covers containers only, and two VMs had no `discard`, so space freed inside them never went back to the pool.
* ntfy had been accepting pushes that never reached a phone (see the 2026-09-21 diagnosis): `base-url` typo and RAM-only message cache.

## What was built

* **Discard on VM disks:** `scsi0` of VM 101 and VM 150 now has `discard=on`. It is a pending change that only applies on a Proxmox **stop/start** (a guest reboot is not enough). `fstrim.timer` was already enabled inside VM 101 (Debian 13). VM 150's disk (`scsi1`, a raw passthrough of its own 2TB drive `sdd`) holds the PBS datastore, so backups do not land on the thin pool.
* **Autoextend verified:** `dm-event.service` is active, `pve/data` reports `monitored`, `thin_pool_autoextend_threshold=80`, `thin_pool_autoextend_percent=10`. That covers one extension; after that the VG has no free space.
* **Pool alert:** [`thinpool-alert`](../../../hosts/physical/thearchivist/thinpool-guard/thinpool-alert), run by a [systemd timer](../../../hosts/physical/thearchivist/thinpool-guard/thinpool-alert.timer) every 15 min. It pushes once per level crossed: **70% high**, **85% urgent**, and a low-priority "recovered" message when usage drops back below 70%. The worst of data% and metadata% counts. Config: [`/etc/thinpool-alert.conf`](../../../hosts/physical/thearchivist/thinpool-guard/thinpool-alert.conf), 0600, sharing the write-only `homelab` ntfy user/topic with `homelab-update`. The real token is only on the host.
* **ntfy (CT 102):** `/etc/ntfy/server.yml` changes: `base-url: http://nfty.home.arpa` → `http://ntfy.home.arpa`, plus `cache-file: /var/cache/ntfy/cache.db` and `cache-duration: 72h`, so pushes survive restarts and a phone that was offline. Backup: `server.yml.bak-2026-09-28`.
* **Wazuh retention (CT 104):** ISM policy [`wazuh-retention-90d`](../../../hosts/lxc/ct104-wazuh/retention/wazuh-retention-90d.json) deletes `wazuh-alerts-*`, `-archives-*`, `-monitoring-*` and `-statistics-*` indices 90 days after creation. Its `ism_template` covers new indices, and it was attached to the 38 existing ones (28 alerts, 5 monitoring, 5 statistics; 0 failures). [`/etc/cron.d/wazuh-log-retention`](../../../hosts/lxc/ct104-wazuh/retention/wazuh-log-retention.cron) prunes files under `/var/ossec/logs/{alerts,archives}` older than 90 days. Nothing was eligible on the day it was applied (oldest data 2026-09-02, so first deletions around 2026-12-01).
* **Backups of VM configs before the change:** `/root/bak/2026-09-28-thinpool/{101,150}.conf`.

## Issues hit

* **Issue: Wazuh overestimated as the growth threat.**
  Symptom: 104 wazuh is the largest guest disk (64G) and the heaviest writer (~0.23 GiB/h).
  Root cause: that write rate is data rewritten in place, which only costs pool space while a snapshot exists. The indexer holds just **256 MB** (~8 MB/day of alerts); alert logs are 360 MB.
  Fix: none needed for capacity. A 90-day retention cap was added anyway (below), so the index can't grow without limit.
* **Issue: `dmeventd` looked inactive.**
  Symptom: `systemctl is-active dmeventd` → inactive.
  Root cause: wrong unit name; the service is `dm-event.service` (socket-activated) and it is running.
  Fix: none.

## Verification

* Forced test push (`THINPOOL_FORCE=1 thinpool-alert`): curl exit 0, message held in ntfy's on-disk cache.
* Threshold branch tested with a throwaway copy at WARN=50 against the live 60% pool: pushed once, level state 1, **second run did not re-push**. The production state file stayed at 0.
* Timer active, next run 15 min out.

## Follow-ups

Status as of 2026-11-12. Ticked items are closed; the evidence is in *Current state* above or the linked doc.

- [x] `discard=on` applied on VM 101 and VM 150; `fstrim.timer` enabled in PBS.
- [x] Phone receives pushes (alerts topic, 2026-10-13).
- [ ] Add `discard=on` to VM 106 (budget): `qm set 106 --scsi0 local-lvm:vm-106-disk-0,iothread=1,size=32G,discard=on`, then a full stop/start.
- [ ] Weekly trim is too slow for wazuh churn and skips CTs 108–116. The fix is in the repo (commit 1ed7057) but not deployed; see [homelab-update](2026-09-15-homelab-update-guest-coverage.md).

---

## Resume line

* Added level-crossing ntfy alerting (70/85%) to a 2.35x-overprovisioned Proxmox LVM-thin pool and fixed a notification server that had been silently dropping pushes, turning a failure that would freeze every guest at once into an alert days in advance.
