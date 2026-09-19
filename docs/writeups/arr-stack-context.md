# thearchivist — *arr Media Stack Context

**Built:** 2026-09-17
**Host:** `thearchivist` (Proxmox VE, kernel `7.0.14-17-pve`)
**Status:** Infrastructure complete and verified. **One verification check still open** (see Blockers).

---

## 1. Host facts

| Item | Value |
|---|---|
| RAM | 94 GB total, ~82 GB available |
| LAN | `192.168.10.0/24`, gateway `192.168.10.1` |
| DNS (host + most CTs) | `192.168.1.1` — **different subnet, works, unexplained** |
| WAN IP (real) | `35.150.39.64` — **AWS range, not typical residential** |
| Uptime pattern | Powers off nightly, up ~15h/day (62.5%) |

### Storage

| Storage | Type | Backing | Size | Used |
|---|---|---|---|---|
| `archive` | dir | `/dev/sdb1`, **ext4** | ~915 GB | 12.45% (~114 GB) |
| `local` | dir | — | ~66 GB | 25.35% |
| `local-lvm` | lvmthin | — | ~136 GB | 49.49% |

**Critical:** `archive` is a **single disk, ext4, no redundancy, no snapshots.** There is no ZFS on this host. Rollback of a destructive operation is not free — build a manifest first (see §7).

`local-lvm` is a **thin pool at ~49%.** All container rootfs volumes live here. If the pool ever fills, every volume on it corrupts. Watch with `lvs`.

---

## 2. Containers

### Media stack (built 2026-09-17)

| CT | Hostname | IP | Port | Cores | RAM | Startup | Mount |
|---|---|---|---|---|---|---|---|
| 100 | jellyfin | 192.168.10.137 | 8096 | 2 | 2048 | `order=3,up=15,down=60` | `/mnt/pve/archive/data/media` → `/media` |
| 110 | prowlarr | 192.168.10.240 | 9696 | 2 | 1024 | `order=4,up=15,down=60` | none |
| 111 | sonarr | 192.168.10.241 | 8989 | 2 | 1024 | `order=5,up=15,down=60` | `/mnt/pve/archive/data` → `/data` |
| 112 | radarr | 192.168.10.242 | 7878 | 2 | 1024 | `order=6,up=15,down=60` | `/mnt/pve/archive/data` → `/data` |
| 113 | qbittorrent | 192.168.10.243 | 8090 | 4 | 4096 | `order=7,up=15,down=180` | `/mnt/pve/archive/data` → `/data` |
| 114 | flaresolverr | 192.168.10.244 | 8191 | — | 2048 | *(unconfirmed)* | none |

All unprivileged, Debian 13, `onboot=1`, timezone `America/Chicago`.

### Pre-existing containers (not touched)

`102` ntfy · `103` caddy · `104` wazuh · `105` nuclei-scanner (stopped) · `106` actualbudget (stopped) · `107` dns-audit · `108` immich · `200` vaultwarden

### CT 109 — verify destroyed

A failed Jellyseerr attempt created CT 109 (IP `192.168.10.139`, Debian 12). `pct destroy 109` was issued but **the result was never confirmed.** Check with `pct list` and destroy if still present. Nothing was installed in it; no data to lose.

---

## 3. Storage layout

```
/mnt/pve/archive/data/           ← mounted as /data in CT 111, 112, 113
├── media/                       ← mounted as /media in CT 100 (Jellyfin)
│   ├── movies/                  (16 flat .mkv files, no year in filename)
│   └── TV_Shows/                (Firefly, Three_Stooges)
└── torrents/
    ├── incomplete/
    └── complete/
```

Everything owned `100000:100000`.

### Why this layout — do not change it casually

**One mount, one path, everywhere.** CT 111, 112, and 113 all mount the same parent at the same path `/data`. This is what lets Sonarr/Radarr take a path qBittorrent reports and open it directly. **No Remote Path Mappings are configured or needed.**

**Downloads and library share one filesystem**, so imports hardlink instead of copying. Instant import, zero duplicate disk usage, and qBittorrent keeps seeding the exact blocks Jellyfin serves. Splitting them across filesystems silently doubles disk usage on every import.

**Jellyfin's mount path is `/media` on the container side.** The host path changed during the restructure but the container path did not, which is why Jellyfin's library survived with no re-identification.

### Ownership model — the one gotcha

The community scripts run all services as **root inside the container**. Unprivileged LXC maps container UID 0 → host UID 100000. That's why everything is `100000:100000` and why no `lxc.idmap` or `chgrp` work was needed.

> **Any host directory you create for these containers must be `chown 100000:100000`.** Host `root:root` is a *different identity* and appears as `nobody:nogroup` inside the container.

---

## 4. VPN configuration (CT 113 only)

| Item | Value |
|---|---|
| Provider | AirVPN |
| Interface | `wg0` (kernel WireGuard — userspace fallback not needed) |
| Config | `/etc/wireguard/wg0.conf` (mode 600) |
| Tunnel IP | `10.146.102.84/32` |
| Endpoint | `204.8.98.82:1637` |
| Exit IP | `204.8.98.86` |
| MTU | **1320** — set by AirVPN, do not change |
| DNS | `10.128.0.1` (AirVPN internal, **resolves only inside the tunnel**) |
| Forwarded port | **22507** — reserved in AirVPN client area, matches qBittorrent |

### systemd drop-ins on CT 113

`/etc/systemd/system/qbittorrent-nox.service.d/override.conf`
```ini
[Service]
TimeoutStopSec=150
UMask=0002
```

`/etc/systemd/system/qbittorrent-nox.service.d/vpn.conf`
```ini
[Unit]
Requires=wg-quick@wg0.service
After=wg-quick@wg0.service
```

`wg-quick@wg0` is **enabled** and starts at boot.

### Why each piece exists

- **`TimeoutStopSec=150`** inside the container's `down=180` — qBittorrent must flush fastresume data for every torrent before exiting. systemd's 90s default would SIGKILL it first, causing force-rechecks or lost torrent state on the nightly power-off.
- **`Requires=`** — qBittorrent refuses to start if the tunnel is down. Not running beats running unprotected. Note this governs *startup* only; a mid-session tunnel drop leaves qBittorrent running but with no route out (fail-closed by routing).
- **`10.128.0.1` DNS** — a second fail-closed layer. No tunnel, no name resolution.

### qBittorrent settings

- **Options → Advanced → Network Interface: `wg0`** — the kill switch. If the interface vanishes, qBittorrent cannot bind a socket. Structural, not policy.
- **Options → Web UI → IP address: `*`** — keeps the UI on `eth0` regardless of peer binding.
- **Options → Connection:** port `22507`, UPnP/NAT-PMP **unchecked**.
- **Options → Downloads:** Default Save Path `/data/torrents/complete`, incomplete `/data/torrents/incomplete`, ATM **Automatic**, pre-allocate **on**.
- **Options → BitTorrent:** DHT **on**, PEX **on**, **LPD off** (it binds `0.0.0.0:6771`, outside the tunnel, and broadcasts torrent activity to the LAN).
- **Seeding limits: off** — auto-removal on a box down 9h/day causes hit-and-runs.

### CT 110 / CT 114 — VPN present but DISABLED

Prowlarr and FlareSolverr were tunneled, then deliberately untunneled. Both now exit on the real IP `35.150.39.64`.

Still in place on both: `/etc/wireguard/wg0.conf`, `/dev/net/tun` passthrough in the LXC config. Backups at `/root/110.conf.bak` and `/root/114.conf.bak`.

Disabled: `wg-quick@wg0` (systemd), the `vpn.conf` drop-ins (deleted), nameserver reverted to `192.168.1.1`.

**Why untunneled:** indexers time out or reject datacenter exit IPs; private trackers flag IP inconsistency across login/search/announce as account sharing; and a dropped tunnel means searches silently fail. The traffic that generates DMCA notices is swarm traffic, which is qBittorrent's and is tunneled.

**To re-enable:** `systemctl enable --now wg-quick@wg0`, restore the `vpn.conf` drop-in, **and** set `pct set <id> --nameserver 10.128.0.1` (the nameserver must change together with the tunnel, or DNS breaks entirely).

---

## 5. Verified — confirmed with output, not assumed

- Hardlink works across `torrents/` and `media/` at filesystem level — same inode, link count 2
- Graceful container shutdown: **12 seconds** (well inside the 180s window)
- Tunnel auto-starts on boot; handshake fresh after full `pct stop`/`pct start`
- **Leak test fail-closed:** `wg-quick down wg0` → `curl` returns nothing. No fallback to `eth0`
- Exit IP `204.8.98.86` vs real `35.150.39.64`
- qBittorrent TCP + UDP peer listeners bound to `10.146.102.84%wg0`
- LPD closed (`0.0.0.0:6771` gone)
- Real 6.5 GB download completed through the tunnel, landed in `complete/` owned `100000:100000`
- Jellyfin library renders with artwork after the storage restructure
- Sonarr/Radarr can write to `/data/media/*`
- Manifest diff after the move: every inode, link count, size, and path identical

---

## 6. BLOCKERS

### B1 — The import + hardlink check has never run *(the open one)*

Everything else is verified. **An actual import has never executed.** The entire §3 storage design exists to make hardlinks happen; if Radarr copies instead, every import silently doubles disk usage on a single non-redundant 915 GB disk.

**Test material already downloaded:** `ubuntu-26.04-desktop-amd64.iso` in `/data/torrents/complete/`, inode `15990789`, link count 1.

**Procedure:**
1. Radarr → **Wanted → Manual Import** → path `/data/torrents/complete`
2. Assign the ISO to any movie (it won't parse; override)
3. **Import Mode: `Hardlink/Copy Files`** ← the setting under test
4. Import

**Check:**
```bash
find /mnt/pve/archive/data/media -type f -newermt '-4 hours' -exec ls -li {} +
```

**Done = inode `15990789` present, link count 2.**

If inodes differ, it copied → check Radarr → Settings → Media Management → *(Advanced)* → **Use Hardlinks instead of Copy**.

Clean up afterward: remove the bogus movie from Radarr with file deletion, delete the torrent + files from qBittorrent.

### B2 — Jellyseerr unavailable upstream

`install/jellyseerr-install.sh` returns **404**. `ct/jellyseerr.sh` still returns 200 but is an orphan (pins Debian 12 while all current scripts use Debian 13). The Gitea mirror returned 503. A GitHub API listing of `install/` shows only `jellyfin-install.sh` — no Jellyseerr under any name.

Not a rename to chase; the file is gone. Retry in ~1 week:
```bash
curl -sI https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/install/jellyseerr-install.sh | head -1
```
200 means it's back.

**Do not hand-build it.** Jellyseerr compiles from source via pnpm and has a long history of installs that report success and leave a dead service, plus major-version upgrades that require `rm -rf dist .next node_modules` before rebuilding.

Planned when available: CT 115, IP `192.168.10.246`, 2 cores / 2048 MB / 8 GB, no mount, `order=10`. Config: sign in with Jellyfin (`http://192.168.10.137:8096`), add Radarr (`192.168.10.242:7878`, root `/data/media/movies`) and Sonarr (`192.168.10.241:8989`, root `/data/media/TV_Shows`), quality profile **Any**, auto-approve **off**.

### B3 — Cloudflare-protected indexers do not work

FlareSolverr is running correctly (solves archive.org in ~4s, memory at 159 MB of 2 GB) but **cannot solve current Cloudflare challenges**:

```
Challenge detected. Title found: Just a moment...
Error solving the challenge. Timeout after 60.0 seconds.
Cloudflare has blocked this request. Probably your IP is banned for this site
```

No setting fixes this. It is the known failure state of the tool — a permanent arms race with Cloudflare.

**Action:** remove the `flaresolverr` tag from indexers that fail this way. Each attempt burns 60s of Prowlarr's time and worsens the health warnings.

### B4 — Only one working indexer

**Internet Archive** is the only indexer testing green. It is public-domain material only — not a general movie source — and its release names don't follow scene conventions, so Radarr frequently can't parse them.

Archive.org torrents are **item-level**: they contain the preservation master plus every derivative encode, thumbnails, and metadata XML. Night of the Living Dead came to **54 GB**; the film itself is 1–2 GB.

**Workaround (manual, per torrent):** Radarr grabs → switch to qBittorrent immediately → **pause** → Content tab → select all → *Do not download* → set only the largest `.mp4` to *Normal* → resume. Radarr has no per-file selection; this must happen in qBittorrent.

**Real fix:** Usenet or private trackers. See §9.

---

## 7. Open loops (non-blocking)

| # | Item | Why it matters |
|---|---|---|
| O1 | Jellyfin library cleanup: `TV_Shows/Firefly/_needs-reencode` (empty), `Firefly/_extras/Firefly - S02E01.nfo` (Firefly has no S02), 13 MakeMKV `.log` files in `Three_Stooges/Season 02` | **Do before Sonarr adopts the library.** Stray dirs become phantom seasons in Sonarr's DB, which is harder to unpick than a filesystem |
| O2 | 16 flat movie files with no year (`A_New_Hope.mkv`, `HTTYD.mkv`, …) | Radarr can't match most of them. Requires a deliberate hand-mapping session, not a side effect of clicking Import. Letting Radarr rename them changes Jellyfin's paths → possible loss of watch state |
| O3 | AirVPN port checker never run against port 22507 | Reserved and set, but inbound openness unconfirmed. Determines whether seeding actually works |
| O4 | Seeding/upload never observed | Ubuntu ISO had 99+ seeds vs ~2 peers — no demand, so it proved nothing |
| O5 | DNS `192.168.1.1` on a `192.168.10.0/24` network | Works, unexplained. Check the OPNsense interface list. An unexplained working path is fragile — if that interface is renumbered, every container loses DNS at once |
| O6 | WAN IP `35.150.39.64` is an AWS range | Unexpected for residential. Worth understanding what's in front of the connection |
| O7 | `api.radarr.video` resolves **AAAA-only**; containers are IPv4-only | May cause Radarr metadata errors. First place to look if they appear |
| O8 | No backups of `/mnt/pve/archive` | Single ext4 disk, no redundancy, no snapshots |
| O9 | Two files in `/root`: `media-manifest-pre.txt`, `media-manifest-post.txt` | Keep as the restructure record, or delete |

### Destructive-op protocol on this host

There is **no ZFS**, so no free snapshot rollback. Before any `chown -R`, `mv`, or mass rename under `/mnt/pve/archive`:

```bash
# 1. Manifest first (inode numbers survive renames within a filesystem)
find /mnt/pve/archive/data/media -printf '%i %n %u:%g %m %s %P\n' | sort > /root/manifest-pre.txt

# 2. Dry run — count and inspect what you're about to touch
find /mnt/pve/archive/data/media -not -group 100000 | wc -l

# 3. Do the thing

# 4. Diff
find /mnt/pve/archive/data/media -printf '%i %n %u:%g %m %s %P\n' | sort > /root/manifest-post.txt
diff /root/manifest-pre.txt /root/manifest-post.txt && echo IDENTICAL
```

---

## 8. Operating the system

### Adding a movie

Radarr → `192.168.10.242:7878` → **Movies → Add New** → search → select correct year
- Root Folder: `/data/media/movies`
- Quality Profile: **Any** (strict profiles reject archive.org releases silently)
- Minimum Availability: Released
- Uncheck *Start search* → Add → click in → **magnifying glass** (Interactive Search)

Interactive Search shows *why* releases were rejected. Red/yellow icons ("Unknown quality", "Unable to parse release title") are normal for archive.org — click the download arrow to force.

### Adding a show

Sonarr → `192.168.10.241:8989` → **Series → Add New**
- Root Folder: `/data/media/TV_Shows`
- Quality Profile: **Any**
- Monitor: as desired — Sonarr then grabs new episodes unattended

### Daily health check

```bash
# Tunnel up and carrying traffic?
pct exec 113 -- wg show

# Exit IP correct? (want 204.8.98.x, NOT 35.150.39.64)
pct exec 113 -- curl -s --max-time 15 https://api.ipify.org; echo

# Services alive?
for id in 110 111 112 113 114; do printf "%s: " $id; pct status $id; done

# Disk headroom
df -h /mnt/pve/archive
lvs
```

### After every nightly boot

`Requires=wg-quick@wg0` means qBittorrent won't start without the tunnel, so `systemctl is-active qbittorrent-nox` returning `active` implies the tunnel came up. Verify occasionally anyway:

```bash
pct exec 113 -- systemctl is-active qbittorrent-nox
pct exec 113 -- curl -s https://api.ipify.org; echo
```

### Shutdown

Proxmox stops containers in **reverse** startup order: qbittorrent(7) → radarr(6) → sonarr(5) → prowlarr(4) → jellyfin(3). Correct — the download client flushes state before the arrs go down.

Never hard-power the host. A SIGKILL'd qBittorrent loses fastresume data → force-recheck of every torrent on next boot, and possible H&R hits.

### Prowlarr indexer sync

Add indexers in **Prowlarr only** (`192.168.10.240:9696`). Full Sync pushes them into Sonarr and Radarr automatically. If they don't appear: Prowlarr → Settings → Apps → *(app)* → **Sync App Indexers**.

Prowlarr backs off indexers that fail repeatedly and won't retry immediately. After fixing a network problem, restart Prowlarr rather than waiting.

---

## 9. Torrent hygiene

### Before downloading anything — verify the tunnel

```bash
pct exec 113 -- wg show
pct exec 113 -- curl -s --max-time 15 https://api.ipify.org; echo
```

Want: recent handshake, climbing transfer, and `204.8.98.x`. **If it returns `35.150.39.64`, stop — you are exposed.**

Mid-download, confirm traffic is actually in the tunnel:
```bash
pct exec 113 -- wg show | grep transfer   # run twice, 10s apart
```
Received bytes should climb at roughly the download rate. If qBittorrent reports 10 MiB/s and `wg show` barely moves, something is bypassing it.

### Periodic kill-switch re-test

```bash
pct exec 113 -- wg-quick down wg0
pct exec 113 -- curl -s --max-time 10 https://api.ipify.org; echo   # MUST be empty
pct exec 113 -- wg-quick up wg0
```

Re-run after any qBittorrent update — the interface binding is a config value and updates can reset it.

### What is and isn't protected

| | Exposure |
|---|---|
| **Protected** | All swarm traffic — peer connections, tracker announces, DHT, PEX. This is where DMCA notices originate |
| **Not protected** | Prowlarr (CT 110) and FlareSolverr (CT 114) indexer contact. Your ISP sees DNS + TLS SNI for indexer domains. `.torrent` file fetches are Radarr/Sonarr, also untunneled |
| **Not eliminated** | AirVPN sees everything you tunnel. Trust moved, not removed. Your protection against swarm logging is their no-logs policy — a policy guarantee, not a cryptographic one |

Visiting an indexer site is not what triggers enforcement. Being logged in a swarm is. The important half is covered.

### Strongest available proof

Run a torrent IP-check magnet (ipleak.net and similar offer one). It reports the IP your client announced with, from the swarm's perspective — real end-to-end proof rather than inference from `curl`.

### Seeding on a 15h/day box

- **62.5% uptime** → seed-time requirements stretch ~1.6× in wall clock. A 72h H&R requirement becomes ~115 real hours (just under 5 days). Trackers typically allow 2–4 weeks, so this clears comfortably
- **Do not enable auto-removal** on ratio or seed time. Torrents going dark between sessions is expected; auto-removal is how you self-inflict H&Rs
- **Do not enable "Remove Completed"** in Sonarr/Radarr's download client settings — it stops seeding the moment the import finishes
- **Port 22507 must be open** or you're unconnectable: you can download from peers with open ports, but nobody can initiate to you, and upload suffers badly

### Private trackers

- Read the VPN rules **before** connecting an account. Some ban VPN ranges; some flag IP churn as account sharing
- If using a VPN with a private tracker, keep **one consistent exit** — don't present different IPs for login, search, and announce
- Ratio is why the AirVPN forwarded port matters. Without it, seeding barely functions

### Public trackers

- Openly monitored; the VPN is doing real work here
- Cloudflare-fronted ones are currently unusable (B3)

### General

- Archive.org: use the pause-and-select workflow (B4) or download tens of GB you don't want
- Leave legitimate torrents (Linux ISOs, archive.org) seeding — it costs nothing and they rely on it
- Watch `df -h /mnt/pve/archive` — single disk, no redundancy, no snapshots

---

## 10. Recommended next steps

1. **Close B1.** Manual-import the Ubuntu ISO, confirm inode `15990789` with link count 2. Five minutes. Everything else is built on the assumption this works
2. **Run the AirVPN port checker** against 22507 (O3)
3. **Jellyfin library cleanup** (O1) before Sonarr adopts `TV_Shows`
4. **Decide on Usenet.** Still the best fit for a box that sleeps 9h/day: no seeding obligation, no ratio, no Cloudflare, retention in years, and a missed window is always recoverable. Needs SABnzbd or NZBGet — one more container on the CT 113 pattern, no VPN required (TLS direct to provider). This was the original recommendation and B3/B4 reinforce it
5. **Retry Jellyseerr** in ~1 week (B2)
6. **Back up `/mnt/pve/archive`** (O8) — a single ext4 disk with no snapshots holds everything

---

## Quick reference

```
Jellyfin      http://192.168.10.137:8096
Prowlarr      http://192.168.10.240:9696
Sonarr        http://192.168.10.241:8989
Radarr        http://192.168.10.242:7878
qBittorrent   http://192.168.10.243:8090
FlareSolverr  http://192.168.10.244:8191

Media         /mnt/pve/archive/data/media     → /media  (CT 100)
Data root     /mnt/pve/archive/data           → /data   (CT 111,112,113)
Downloads     /mnt/pve/archive/data/torrents/{incomplete,complete}

Real IP       35.150.39.64
VPN exit      204.8.98.86        (CT 113 only)
Fwd port      22507
```

API keys for Prowlarr, Sonarr, and Radarr are stored in Vaultwarden (CT 200), along with the qBittorrent and Prowlarr web credentials.
