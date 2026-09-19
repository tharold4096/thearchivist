# Weekly Patch Orchestrator — Guest Coverage, Hold Gates, Thin-Pool Guard

**Date:** 2026-09-15
**Machine(s):** The Archivist (Proxmox VE, Dell R710) — LXCs 100, 102, 103, 104, 107, 200; VM 101 samba-vm
**Status:** Complete (monitoring). All 6 running containers covered; 100 and 107 have no rollback point by choice. The samba-vm agent-restart path has so far been proven only in a sandbox.
**Tags:** patching, proxmox, lxc, lvm-thin, snapshots, wazuh, qemu-guest-agent, systemd

---

## Why I built this

An audit of the 2026-09-13 Sunday patch run found three problems in
`homelab-update`, the systemd-timer-driven patch orchestrator on the Archivist:

* **No container had ever been patched by it.** `LXC_IDS=(0 0 0)  <-- SET ME`
  was never filled in, so every weekly report since 2026-08-27 had an empty
  Containers section and the run still reported success. Only the host and
  samba-vm were actually in scope.
* **samba-vm's run was reported FAILED, but the real damage was worse than a
  failure:** dpkg was killed mid-configure and left packages half-configured
  until a manual `dpkg --configure` the next evening.
* **A Wazuh agent pin gap.** `wazuh-agent` was installed in samba-vm on
  2026-09-14 with no apt hold. The script only checked holds on the host, and
  only *after* upgrading it, so the next Sunday could have pushed that agent
  ahead of the manager in LXC 104.

## How I built it

* **Tools/stack:** bash, systemd timer/oneshot service, `pct`/`qm` (incl. the
  QEMU guest agent), LVM-thin snapshots, apt holds, ntfy (LXC 102).
* **Key steps:**
  * Read-only audit first: Sunday's report, the service journal, host and
    guest `apt/history.log` and `dpkg.log`, PVE task history, per-CT apt
    state, and snapshot/config mtimes for stopped guests.
  * Drafted the change against a copy of the live script, then tested the
    new logic locally with stubbed `pct`/`qm`/`lvs`/`systemd-run`: 12
    container-gate paths, the guest-agent JSON parser (success, guest failure,
    timeout, agent down, garbage), and the detached-apt launch string executed
    in a sandbox for apt exit 0, apt exit 100 and a half-configured dpkg.
  * Measured the thin pool and per-disk write volume before deciding whether
    the Wazuh snapshot could be afforded (numbers below).
  * Deployed via staged temp name with checksum gates: verify the live file
    is unchanged → upload as `.new` → dry run (expected exactly one failure,
    the missing samba-vm hold) → `apt-mark hold wazuh-agent` in samba-vm → dry
    run (expected 0 failures) → back up live → `mv` into place.
  * Ran the first real pass through `homelab-update.service` itself, the same
    unit the timer fires, and verified each guest afterwards.
* **What changed in the script:**
  * `LXC_IDS=(107 100 104 200 102 103)`: least disruptive first, ntfy
    second-last (the final push needs it), Caddy last. Stopped 105 and 106
    deliberately left out.
  * Per-container pipeline `process_ct`: running? → holds → retire last
    week's snapshot → thin-pool check → snapshot → apt. Every gate fails
    closed. No hold, no pool headroom, or no snapshot means no apt.
  * `EXPECTED_HOLDS` map (`host`, `ct:104`, `vm:101`) checked **before** each
    target is touched. A missing pin blocks that target and reports FAILED.
  * samba-vm apt runs detached from the guest agent via `systemd-run`. The
    host polls for an exit-code file and then requires `dpkg --audit` to be
    clean.
  * `DROP_SNAPSHOT_IDS=(104)`: Wazuh's snapshot is removed as soon as its
    update is clean.
  * `NO_SNAPSHOT_IDS=(100 107)`: containers PVE cannot snapshot are updated
    with no rollback point, a deliberate choice. They skip the snapshot and
    pool gates but not the hold gate, and every report says "updating WITHOUT
    a rollback point" so it never becomes a silent assumption.
  * `trim_cts`: `pct fstrim` on every running listed container after the
    updates (pct skips bind mounts), reporting the pool's data % before and
    after. That's the real reclaimed figure, not fstrim's own.
  * Host `apt-get update` retried up to 10× at 30 s intervals (see What broke).
  * `dry-run` no longer sends the ntfy push, repoints `latest.md` or prunes
    reports. It writes only `<stamp>.dry.md`.
* **Other host changes:** `pct set 100 --onboot 1` (jellyfin now starts at
  boot); `apt-mark hold wazuh-agent` inside VM 101; `pct fstrim 104`.
* **Config/scripts:** [`homelab-update/homelab-update`](homelab-update/homelab-update)
  (repo copy with `NTFY_TOKEN="<SET-ON-HOST>"`; the real token lives only in
  `/usr/local/sbin/homelab-update` on the Archivist),
  [`homelab-update.timer`](homelab-update/homelab-update.timer),
  [`homelab-update.service`](homelab-update/homelab-update.service).
  Deployed sha256 `f377474e…` (differs from the repo copy only on the token
  line). Backups in `/usr/local/sbin/`: `.bak-pre-guestcoverage-20260915`
  (pre-rework), `.bak-pre-nosnapshot-20260915` (`82879c3e…`),
  `.bak-pre-fstrim-20260915` (`b55374a1…`).

## What broke

* **Issue: samba-vm upgrade killed itself mid-dpkg.
  Symptom:** Sunday's report said `FAILED: samba-vm (101) apt via guest agent`.
  The VM's apt history had a `Start-Date` with no `End-Date`, and `dpkg.log`
  ended at `half-configured qemu-guest-agent` at 08:23:21.
  **Root cause:** apt ran as a child of `qemu-guest-agent` via
  `qm guest exec`. The upgrade included `qemu-guest-agent` itself, and its
  postinst restarted the unit. The unit is `KillMode=control-group`, so the
  restart killed everything it had spawned, apt and dpkg included.
  **Fix:** apt now runs in its own transient unit via `systemd-run`, writes
  its exit code to a file, and the host polls for that file, tolerating the
  agent being unreachable mid-poll. Exit 0 is not accepted alone:
  `dpkg --audit` must also be empty.

* **Issue: The update list was never filled in, and nothing noticed.
  Symptom:** Empty Containers section in every report; exit 0.
  **Root cause:** A placeholder that is silently skipped is indistinguishable
  from "nothing to do."
  **Fix:** IDs set from `pct list`, and the report now lists every container
  with an explicit outcome (updated / not running / FAILED with reason).

* **Issue: Holds verified after the upgrade that would break them, and only on
  the host.
  Symptom:** `report_holds` ran at the end of the run and only read the
  host's `apt-mark showhold`.
  **Root cause:** Written when the only agent was on the host.
  **Fix:** Per-target expected holds checked *before* each target is updated;
  unreadable holds count as missing.

* **Issue: Containers with bind mounts cannot be snapshotted.
  Symptom:** First real run: `FAILED: snapshot of dns-audit (107)` and
  `jellyfin (100)`. PVE task log: `TASK ERROR: snapshot feature is not available`.
  **Root cause:** 100 bind-mounts `/mnt/pve/archive/media`; 107 bind-mounts
  `/mnt/pve/archive/dnslogs` and `/mnt/pve/archive/models`. PVE refuses to
  snapshot any container with host bind mounts. I had checked mountpoints
  before the run and wrongly assumed they would be skipped. That is how
  vzdump backups treat them, not snapshots.
  **Fix:** The gate failed closed as designed, so neither container was
  updated on the first run. Options were a vzdump to `archive` before each
  update, updating without rollback, or manual patching. I chose updating
  without rollback, because rebuilding either container from config is
  within reach. Added `NO_SNAPSHOT_IDS=(100 107)`, deployed via the same
  checksum-gated staged swap, and patched both by hand with the script's
  exact apt command. A second full run would have replaced the fresh
  pre-update snapshots of 200/102/103 with post-update ones.

* **Issue: Proxmox's own daily apt run can collide with the patch run.
  Symptom:** Found while verifying unattended readiness. On 2026-09-13 the
  PVE task log shows an `aptupdate` task at 08:25:22, while the host
  dist-upgrade was running (08:24:11–08:25:55).
  **Root cause:** `pve-daily-update.timer` is `OnCalendar=01:00` with
  `RandomizedDelaySec=5h` and `Persistent=true`. The box is off overnight, so
  it catches up after the 07:45 wake at a random time; over nine days it ran
  anywhere from 08:25 to 12:28. It runs `apt-get update`. I tested apt 3.0.3
  against a held lists lock in a scratch directory: it fails immediately with
  "Could not get lock", and neither `DPkg::Lock::Timeout` nor
  `Acquire::Lock::Timeout` makes it wait. Sunday's overlap happened to miss
  the host's own `apt-get update` by about 70 s.
  **Fix:** Host `apt-get update` retries up to 10× at 30 s intervals, and
  dist-upgrade never runs unless an update succeeded (both tested with a
  stubbed apt).

* **Issue: fstrim's "42 GB" was not what it reclaimed.
  Symptom:** `pct fstrim 104` reported 42 GB trimmed, against a 21 GiB
  estimate.
  **Root cause:** fstrim reports every free extent it discards. On a first
  trim that is the filesystem's entire free space (40 GiB available plus
  ext4 reserved blocks), most of which was never allocated in the thin pool
  and so frees nothing there.
  **Fix:** Measured at the pool instead. vm-104 went 64.01% → 32.40% of
  64 GiB (40.97 → 20.74 GiB, −20.2 GiB) and `pve/data` went 54.94% → 39.98%
  (−20.4 GiB), matching the estimate of mapped minus used.

* **Issue: A stale snapshot could outlive a tripped pool guard.
  Symptom:** Found while working out the space budget, before deploy.
  **Root cause:** Last week's `preupdate` snapshot was deleted only
  immediately before taking a new one. If the pool check tripped, deletion
  was skipped, and the snapshot most likely filling the pool would grow for
  another week.
  **Fix:** Stale snapshot retired before the pool check.

* **Issue: Concurrent edit of the live script during drafting.
  Symptom:** Live checksum changed from `fc7a4978…` to `9bf78a9a…` between
  drafting and staging.
  **Root cause:** A manual `nano` edit at 16:24 set `LXC_IDS` directly.
  **Fix:** Checksum gate caught it before overwrite. Confirmed intentional,
  draft ordering chosen, and the manually edited version kept as the backup.

## What worked

**Space for the Wazuh snapshot, measured rather than assumed** (2026-09-15, 8.65 h uptime):

| Quantity | Value |
|---|---|
| Thin pool `pve/data` | 136.47 GiB; 73.07 GiB used (53.54%); 63.4 GiB free; metadata 3% |
| Autoextend | at 80%, +10%; VG has 16 GiB free, so one extension possible (to ~150 GiB) |
| Pool behaviour when full | `queue_if_no_space`, so every guest on the pool hangs, then errors |
| vm-104 mapped blocks | 41.0 GiB mapped (64.01%) vs 20 GiB used by ext4, since freed blocks are not being trimmed |
| vm-104 writes | 1.96 GiB since boot, about 0.23 GiB/h (roughly 3.4 GiB/day of uptime) |
| All other snapshotted CTs | 0.40 GiB since boot combined |

A thin snapshot's extra cost is bounded by the origin's mapped blocks that get
overwritten while it exists, and in practice by write volume:

* **As deployed (104 dropped after a clean update):** it existed for roughly a
  minute. Pool went 53.55% → 54.94% for the whole run, including every
  container's package changes and the three snapshots kept all week. The
  week's growth from the kept snapshots is bounded by their writes, about
  5 GiB, which ends near 58%.
* **If 104's update fails and its snapshot is kept a week:** at most about
  24 GiB (bounded by writes) plus 5 GiB, which ends near 75%. That is right at
  the guard and below autoextend.
* **Theoretical ceiling** (every mapped block of every snapshotted CT
  overwritten): about 132 GiB, or 97% of today's pool. Autoextend would take
  that to about 88% of 150 GiB. It does not fill, but only because of
  autoextend.

**First real run (2026-09-15 16:43–16:50, via `homelab-update.service`):**

* 104 wazuh (86 package actions; snapshot taken then dropped), 200 vaultwarden
  (88), 102 ntfy (84), 103 caddy (78): all updated, all running afterwards.
  `wazuh-manager/indexer/dashboard`, `ntfy` and `caddy` active; 0 failed
  units in 200.
* Wazuh versions still aligned: manager, indexer, dashboard, host agent and
  samba-vm agent all `4.14.7-1`; holds intact in all three places.
* samba-vm: detached apt unit ran, exit-code file `0`, `dpkg --audit` clean,
  0 packages pending. There were no packages to upgrade this time, so the
  agent-restart case was not exercised on real hardware (covered only by the
  sandbox test).
* Host dist-upgrade OK; kernel `7.0.14-17-pve` staged for the 23:00 cycle.
* ntfy push published (`messages_published=1` in ntfy's stats after its own
  update).
* Exit status 1, by design: the two snapshot-incompatible containers.

**Follow-up (16:59–17:01):** 107 dns-audit (112 package actions) and 100
jellyfin (140) patched with the script's apt command; log at
`/var/log/homelab-update/2026-09-15_manual-100-107.log`. Both have complete
apt history entries, a clean `dpkg --audit`, and no new failed units (the one
failed unit in 100 is Ubuntu's `motd-news.service`, failing since 13:23,
before the update). jellyfin 12.1 active; `dnsaudit.timer` scheduled. The
dry run with `NO_SNAPSHOT_IDS` exits 0. After the trim the pool is at 40.13%.

**Trim scheduling (evening):** A dry run of the trim build under `systemd-run`
(the service's clean environment) exited 0. To prove the real command before
Sunday, I ran `pct fstrim` once by hand on the five containers not yet
trimmed, 3–4 s each, all rc 0, root filesystems only (bind mounts skipped):

| CT | fstrim reported | LV data % before → after |
|---|---|---|
| 107 dns-audit | 29.9 GiB | 6.32 → 6.48 |
| 100 jellyfin | 13.6 GiB | 50.99 → 15.01 |
| 200 vaultwarden | 10.4 GiB | 44.69 → 13.60 |
| 102 ntfy | 970 MiB | 62.18 → 53.09 |
| 103 caddy | 2.9 GiB | 30.25 → 27.33 |

The pool went 40.13% → 35.68% (−6.1 GiB) against 57.8 GiB "trimmed". Most of
the gap is fstrim counting free space that was never allocated. The rest is
the snapshot lag: 200, 102 and 103 still hold this afternoon's `preupdate`
snapshots, so their freed blocks (about 3.7 GiB in 200 alone) return to the
pool only when those snapshots are retired on Sunday.

**Unattended readiness for Sun 2026-09-20:** timer enabled and active, next
elapse 08:19:23, `Persistent=yes`; `systemd-analyze verify` clean. The wake
alarm is re-armed nightly by `nightly-poweroff.sh`, and there were 8
consecutive 07:49 boots. The script has now run under systemd both for real
and as a dry run. Holds are present on all three targets, the pool is at 36%,
ntfy delivery to the phone is confirmed, and there is no unattended-upgrades
on the host to fight over dpkg.

## What I'd do differently

* Test snapshot support per container during dry-run. The dry run reported
  "would snapshot" for 100 and 107 because it never asked PVE. It should
  check for bind mounts or query snapshot capability.
* Don't discard `pct`'s stderr. The script's `>/dev/null 2>&1` on
  `pct snapshot` hid "snapshot feature is not available" and cost a trip to
  the task log.
* Treat a placeholder config value as a hard error, not a silent skip.
* Trim from day one of thin provisioning. Trimming 104 alone reclaimed
  20.4 GiB of blocks ext4 had already freed. Those blocks had inflated the
  pool and the worst case for any snapshot of 104. Weekly trim is now part
  of the patch run.
* Read space reclaimed at the pool (`lvs`), never from a tool's own report.

**Open:**

* The samba-vm agent-restart path has not yet run on real hardware.
* jellyfin's `onboot=1` takes effect at the 2026-09-16 07:45 wake and has
  not been observed yet.

---

## Resume-ready summary

* Audited a Proxmox patch orchestrator and found it had never updated any of
  six LXC containers, silently skipped by an unset placeholder. Traced a
  "failed" VM upgrade to the QEMU guest agent killing its own dpkg child under
  `KillMode=control-group`, and redesigned the VM path around a detached
  systemd unit with exit-code polling and dpkg integrity checks.
* Extended automated patching to production containers behind fail-closed
  gates (per-guest apt-hold verification for order-sensitive Wazuh packages,
  an LVM-thin pool headroom guard sized from measured write rates, and
  pre-update snapshots). Deployed via checksum-gated staged swap with two
  dry-run gates. Brought all 6 running containers, 1 VM and the hypervisor
  under patching (588 container package actions on day one) with zero
  version drift across the Wazuh stack. Reclaimed 26.5 GiB (19% of the
  pool) of stale thin-pool allocation and made weekly trim part of the run.
