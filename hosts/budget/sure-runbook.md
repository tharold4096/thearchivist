# Sure runbook (VM 106 `budget`)

Self-hosted Sure (community fork of Maybe Finance). Last verified **2026-10-27**.
No secrets in this file. Real values live only in `/opt/sure/.env` (mode 600) on the VM
and in the backup bundles under `/srv/sure-backups` (root 700).

## 1. Current state

| Item | Value | Status (2026-10-27) |
|---|---|---|
| Host | thearchivist, Proxmox, 192.168.10.202 | |
| VM | **106** `budget`, Debian 13, 192.168.10.206/24 static on `ens18` | PASS |
| VM flags | `onboot: 1`, `agent: enabled=1`; `qm agent 106 ping` OK | PASS (agent fixed today) |
| Resolver | `/etc/resolv.conf` regular file → 192.168.10.1 | PASS |
| Root disk | `scsi0` local-lvm 32G (single SSD, PERC RAID-0, **no redundancy**) | as designed |
| Backup disk | `scsi1` `archive:106/vm-106-disk-0.qcow2` 20G (RAID-1 mirror) → `/srv/sure-backups` | PASS |
| Stack | `/opt/sure`: `compose.yml`, `compose.override.yml`, `.env`, `bin/sure-backup` | |
| Services | `db` (postgres:16), `redis` (redis:latest), `web`, `worker`, `backup`; all `restart: unless-stopped` | PASS |
| Image | `ghcr.io/we-promise/sure:0.7.5-hotfix.3` pinned via `SURE_IMAGE_TAG` (digest `sha256:9cbcc5a2…`) | PASS (pinned today) |
| Encryption | 3 `ACTIVE_RECORD_ENCRYPTION_*` vars in web and worker; no "not configured" logs | PASS |
| Signups | `Setting.onboarding_state = closed` (DB) + `ONBOARDING_STATE=closed` (.env) | PASS (closed today) |
| Proxy | Caddy **CT 103**, 192.168.10.201, `tls internal` | PASS |
| DNS | `budget.home.arpa` → 192.168.10.201 (Unbound override + Tailscale split DNS) | PASS |
| TLS | `curl -sI https://budget.home.arpa` without `-k` → 302 from Omarchy | PASS |
| Port 3000 | Published on `0.0.0.0`, reachable directly, bypassing Caddy | **OPEN ITEM** |
| Healthchecks | `web`/`worker` have none, so "Up" ≠ ready (502 for ~30s after boot) | open item (minor) |
| Backups | daily 18:00 UTC (13:00 CDT / 12:00 CST), keep 7 days, restore tested | PASS |
| Auto-sync | 02:22 UTC (`auto_sync_timezone=UTC`) = 21:22 CDT / 20:22 CST | inside window |

Power schedule: host cron `55 22 * * *` runs `/usr/local/sbin/nightly-poweroff.sh`
(`shutdown -h +5` → 23:00, RTC wake alarm 07:45). VM is up by ~07:53.
**Safe window for anything scheduled: 08:00–22:55 Central.**

## 2. Rebuild from scratch

1. **VM:** Debian 13, VMID 106, `scsi0` on local-lvm 32G, virtio-scsi-single, `net0` vmbr0.
   `qm set 106 --onboot 1 --agent enabled=1`; in guest `apt install qemu-guest-agent docker.io docker-compose` (or Docker CE).
   Static 192.168.10.206/24, gw/DNS 192.168.10.1. `tobias` in group `docker`.
2. **Backup disk** (on the Proxmox host):
   `qm set 106 --scsi1 archive:20,format=qcow2,iothread=1,discard=on`
   Then in the guest, as root (or `qm guest exec 106 -- bash -c "…"`), using the by-id path so `sdX` letters can't bite:
   - `echo ,,L | sfdisk --label gpt /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1`
   - `mkfs.ext4 -L sure-backups /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1-part1`
   - `mkdir -p /srv/sure-backups && chattr +i /srv/sure-backups`. This makes the *unmounted* mountpoint immutable, so a missing disk makes backups fail loudly instead of writing to the SSD.
   - fstab (current line; a rebuilt filesystem gets a new UUID, so take it from `blkid`):
     `UUID=832052b7-81ff-401a-8d6a-bc9fe6816eda /srv/sure-backups ext4 defaults,nofail,x-systemd.device-timeout=10s 0 2`
   - `systemctl daemon-reload && mount /srv/sure-backups && chown root:root /srv/sure-backups && chmod 700 /srv/sure-backups`
3. **Stack:** in `/opt/sure`: `compose.yml` from Sure's `compose.example.yml`;
   `compose.override.yml` = [`compose.override.yml`](compose.override.yml);
   `bin/sure-backup` from `https://raw.githubusercontent.com/we-promise/sure/main/bin/sure-backup` (mode 755; **read it before running**; the reviewed copy had sha256 `e6abffec7bb5…469691`).
   Or skip all of this and run `restore.sh` from a backup bundle (section 4), which recreates config too.
4. **`.env`** (mode 600, owner tobias). Keys that must be set, **names only**:
   - Required secrets: `SECRET_KEY_BASE`, `POSTGRES_PASSWORD`, `ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY`, `ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY`, `ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT`
   - Required plain: `SELF_HOSTED`, `POSTGRES_USER`, `DB_HOST`, `DB_PORT`, `REDIS_URL`, `PORT=3000`, `APP_DOMAIN`, `SURE_IMAGE_TAG=0.7.5-hotfix.3`, `ONBOARDING_STATE=closed`
   - Backups: `BACKUP_DIR=/srv/sure-backups`, `BACKUP_SCHEDULE="0 18 * * *"`, `BACKUP_KEEP_DAYS=7`
   - Present but empty (from the example file): `OPENAI_*`, `LANGFUSE_*`, `TWELVE_DATA_API_KEY`, `BRAND_FETCH_CLIENT_ID`, `CHIMNIE_API_KEY`, `SMTP_*`, `EMAIL_SENDER`, `OIDC_*`, `WEBAUTHN_*`, `POSTHOG_*`, `SKYLIGHT_*`, `EXCHANGE_RATE_PROVIDER`, `SECURITIES_PROVIDER`, `PRODUCT_NAME`, `BRAND_NAME`
   - `RAILS_ASSUME_SSL=true` is set in the stack (TLS terminates at Caddy).
   - **Without the original `SECRET_KEY_BASE` and `ACTIVE_RECORD_ENCRYPTION_*` values, encrypted columns are unreadable.** They are in every backup's `config/.env`.
5. `docker compose up -d && docker compose --profile backup up -d backup`
6. **Caddy** (CT 103, `/etc/caddy/Caddyfile`; back it up first like the existing `Caddyfile.bak-*`):
   [`Caddyfile.budget.fragment`](Caddyfile.budget.fragment):
   ```
   budget.home.arpa {
   	tls internal
   	reverse_proxy 192.168.10.206:3000
   }
   ```
   DNS: Unbound host override `budget.home.arpa → 192.168.10.201` on OPNsense; Tailscale split DNS for `home.arpa`.
7. Close signups: `docker compose exec web bin/rails runner 'Setting.onboarding_state = "closed"'`.

## 3. Backups

- **Layout:** `/srv/sure-backups/<version>/<UTC-stamp>-<manual|scheduled>/` with `db.dump` (pg_dump 17 custom format),
  `storage.tar.gz`, `config/` (`.env`, compose files, `bin/sure-backup`), `manifest.json`, `restore.sh`, `SHA256SUMS`.
- **Manual (before every upgrade):** `cd /opt/sure && docker compose run --rm backup create`
- **List:** `docker compose run --rm backup list` (the folder is root-only, so use the container rather than `ls` as tobias)
- **Verify a bundle:** `sudo sh -c 'cd /srv/sure-backups/<ver>/<name> && sha256sum -c SHA256SUMS'`
- **Schedule math** (`BACKUP_SCHEDULE` is UTC; window 08:00–22:55 Central):
  CDT (UTC−5) window = 13:00→03:55 UTC; CST (UTC−6) = 14:00→04:55 UTC; overlap **14:00→03:55 UTC**.
  `0 18 * * *` = 13:00 CDT / 12:00 CST: mid-window, clear of PBS (21:00 local) and auto-sync (02:22 UTC).
- **Retention:** scheduled bundles older than 7 days are pruned; manual bundles are kept until you delete them.
- **Also covered by PBS:** the nightly 21:00 vzdump job (`all 1`) includes VM 106, both disks.
- **Why the override exists:** `0.7.5-hotfix.3` ships only the old `bin/db-backup.sh`. The override mounts the
  standalone script where the `backup` service's entrypoint expects it. **On upgrade to an image that has
  `bin/sure-backup`, delete `compose.override.yml` and `bin/`**, or the old script will keep hiding the new one.
- **Upgrade:** `docker compose run --rm backup create`, then set `SURE_IMAGE_TAG=<new>` in `.env`, then `docker compose pull web worker backup && docker compose up -d && docker compose --profile backup up -d backup`
- **In-place rollback:** `docker compose stop web worker && docker compose run --rm backup restore <ver>/<name>`, set `SURE_IMAGE_TAG` back, then `docker compose up -d`.

## 4. Restore procedure (tested 2026-10-27)

Restores into a **separate** project; it never touches the live one. The folder name becomes the project name.

1. Pick the bundle: `docker compose run --rm backup list`
2. As root (the bundle is root-only):
   `sudo sh /srv/sure-backups/<ver>/<name>/restore.sh --target /tmp/sure-restore-test --port 3001 --without-worker --yes`
   **Always `--without-worker` while the live instance runs.** Otherwise both workers sync the same bank connections (SimpleFIN tokens can rotate) and recurring jobs run twice.
3. Check it: `curl -s -o /dev/null -w '%{http_code}\n' http://192.168.10.206:3001/up` should print 200.
   Compare counts: `docker exec sure-restore-test-web-1 bin/rails runner 'puts [User.count, Account.count, Entry.count].inspect'` against the same command in `/opt/sure` (`docker compose exec web …`).
4. Tear down **only the test project**. Dry-run first:
   `docker ps -a --filter label=com.docker.compose.project=sure-restore-test --format '{{.Names}}'` and
   `docker volume ls -q --filter label=com.docker.compose.project=sure-restore-test` should list only `sure-restore-test*`. Then:
   `sudo sh -c 'cd /tmp/sure-restore-test && docker compose -p sure-restore-test down -v --remove-orphans && cd / && rm -rf /tmp/sure-restore-test'`
5. Confirm the live instance is unaffected: `cd /opt/sure && docker compose ps` (uptimes unchanged), `docker volume ls` (still `sure_*`).

The 2026-10-27 test of bundle `0.7.5-hotfix.3/2026-10-27_163212-manual`: checksums 8/8 OK; restored `/up` returned 200;
counts matched live (users=1 families=1 accounts=0 entries=0, onboarding=closed); teardown left 0 containers and 0 volumes;
live containers kept running without interruption. **Data was nearly empty at the time, so re-run this test after the WF import.**

**Disaster recovery onto a fresh VM:** rebuild steps 1–2, copy a bundle off the archive disk
(or attach the qcow2 to the new VM), then run `sh <bundle>/restore.sh --target /opt/sure-restored --port 3000 --with-worker`
**only if the old instance is gone**. Update the Caddy upstream if the IP changes.

## 5. Phase 3 checklist (before buying SimpleFIN)

Scripts live next to this file. All are read-only and run from Omarchy.

- [ ] **API key.** In the UI: avatar → **Settings → API Key** (`/settings/api_keys`) → create a key with **Read** scope, then copy it (it is shown once; store it in Vaultwarden).
      Run `bash sure-api-check.sh` (it prompts silently for the key). Expect `HTTP 200` and the shape `{"accounts":[{…}], "pagination":{"page","per_page","total_count","total_pages"}}` (from `app/views/api/v1/accounts/index.json.jbuilder`).
      Header: `X-Api-Key: <key>` (source: `app/controllers/api/v1/base_controller.rb:110`). OAuth tokens use `Authorization: Bearer` instead.
- [ ] **Wells Fargo CSV.** In the UI: **Import** (`/imports`) → New import → Transactions (CSV).
      Sure needs at least one account first: create it by hand (`/depositories/new`, subtype Checking). The "Import accounts first" message is misleading.
      Sure parses CSV with `headers: true`, so **check the first line before importing** (`head -1 file.csv`). WF's current export already has
      `"DATE","DESCRIPTION","AMOUNT","CHECK #","STATUS"`, so upload it unchanged. Only an old-style file whose first line is a transaction needs a header added,
      and that must go to a **new** filename: `{ echo 'Date,Amount,Flag,Check,Description'; cat in.csv; } > out.csv`. Never redirect onto the input; the shell empties it first.
      Map Date → `DATE` (MM/DD/YYYY), Amount → `AMOUNT`, Name → `DESCRIPTION`. In WF exports, negative = money out.
      Verify: `bash sure-wf-verify.sh Checking1.csv`. The `CSV rows`/range must equal the account's `txns`/range, with `dup_groups=0`
      (any hit: check in the UI; identical same-day charges can be real).
      Then take a manual backup and repeat the section 4 restore test, so the restore is proven with real data.
- [ ] **Power-cycle survival.** Each morning after a 23:00 → 07:45 cycle: `bash sure-powercycle-check.sh`.
      Expect all PASS: guest agent; previous boot ended with `Reached target poweroff.target` + `Journal stopped`;
      db/redis/web/worker/backup running and started on their own within 10 min of boot; backup disk mounted;
      latest scheduled backup ≤ 26h old with valid checksums; HTTPS 2xx/3xx.
- [ ] **Sync timing.** Auto-sync 02:22 UTC (`Setting.auto_sync_timezone = UTC`; Sidekiq cron `22 2 * * *`) =
      **21:22 CDT** (until Sun Nov 1) / **20:22 CST** (after), both inside the 08:00–22:55 window. Note: a sync that is missed while the host is off is not caught up.
      Other jobs: `clean_inactive_families` (04:00 UTC) lands at 23:00 CDT, which is off, until Nov 1, then 22:00 CST, which is on; it's harmless either way.

### Definition of done

**7 consecutive days** where all of these hold:
1. `https://budget.home.arpa` is reachable from the laptop **and** the phone,
2. a scheduled backup lands daily in `/srv/sure-backups` (`sure-powercycle-check.sh` passes the backup line),
3. the containers survive every power cycle (`sure-powercycle-check.sh` reports `RESULT: power cycle survived`), and
4. the WF CSV data is intact (`sure-wf-verify.sh` counts unchanged, `dup_groups=0`).

Only then buy SimpleFIN ($15/yr).

## 6. Secrets: where they sit

- Live: `/opt/sure/.env` (600 tobias) on the SSD; `.env.bak-20261027` and `.env.bak-20261027b` beside it (600). Delete them once the changes are settled.
- Every backup: `/srv/sure-backups/**/config/.env` (root 700/600) on the RAID-1 mirror.
- PBS: nightly image backups of both VM disks contain all of the above.
- Vaultwarden (CT 200) is the right home for the master copy of `SECRET_KEY_BASE` + the 3 encryption values and the Sure API key.
- **Off-site (later session):** use the `backup-offsite` service (rclone, hourly copy, read-only mount of `/srv/sure-backups`).
  It needs `BACKUP_DESTINATION` pointing at an **rclone crypt** remote layered over the real remote, defined with `RCLONE_CONFIG_<NAME>_*` vars in `.env`
  (the crypt `password` and `password2` must be obscured with `rclone obscure`). Store the crypt passwords in Vaultwarden too: they end up inside
  `.env`, which is inside the encrypted bundles, so losing the VM would otherwise lock you out of your own off-site copy.

## 6b. Auto-categorization (Responder, CT 116)

A daily 09:00 job on Responder categorizes new uncategorized transactions through the API: Claude proposes, code applies `category_id` only, at high or medium confidence.
Setup, operation, undo and kill switch: [`categorize-setup.md`](categorize-setup.md). Code: `../responder/categorize.py`.
Restore test rerun with real data on 2026-10-28: bundle `2026-10-28_190912-manual`, 369 transactions, range 2024-10-28..2026-10-27, amount checksum matched live.

## 7. Open items

- [ ] **Port 3000 exposure.** Restrict it in the `DOCKER-USER` chain: allow `192.168.10.201` → tcp/3000, drop everything else to 3000; persist it with a systemd unit.
      ufw is *not* a fix (Docker-published ports bypass it). The Proxmox VM firewall would need the datacenter firewall enabled. Binding to a single IP limits the interface, not the sources.
- [ ] Off-site encrypted copy (section 6).
- [ ] Phone trust for the Caddy internal CA: install the root from CT 103 `/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt`, which belongs to the caddy service user.
      A second CA also exists under `/root/.local/share/caddy/…`, likely from running `caddy` as root once; it is **not** the one serving. Compare `openssl x509 -noout -fingerprint -sha256` against what Omarchy trusts before installing.
- [ ] Remove the old Actual Budget container. Inventory and dry-run first; nothing is deleted until the list is reviewed.
- [ ] Minor: add healthchecks for `web` (`/up`) and `worker`; pin `redis` to a version.
- [ ] On the next Sure upgrade: delete `compose.override.yml` + `bin/` if the new image ships `bin/sure-backup`.
