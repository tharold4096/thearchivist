# Context — LXC resolver and IPv6 behavior on `thearchivist`

**Written September 18, 2026.** **Findings 1 and 2 were remediated the same day — see `docs/writeups/2026-09-18-lxc-resolver-ipv6-jellyfin-ip.md`, which also corrects the IPv6 failure mode (fast `ENETUNREACH`, not a 10s hang).** Background for work on the Proxmox container fleet. This is a description of findings and current state, not a task list.

---

## Environment

- **Host:** `thearchivist`, Dell PowerEdge R710, Proxmox VE. Management segment `192.168.10.0/24`.
- **Gateway:** `sentrygate`, OPNsense inline firewall at `192.168.10.1`. Runs Unbound in full recursive mode with blocklists. **As of 2026-09-18 DNSSEC validation is not active** — running `module-config` is `"python iterator"`, no validator. The DNSBL deliberately does not apply to the Archivist. Also the tailnet subnet router advertising `192.168.10.0/24`.
- **Upstream:** family router at `192.168.1.1`, reachable from the Archivist segment through Sentry Gate's WAN side.
- **Containers:** mostly unprivileged LXCs created via community-scripts helper scripts, networked `ip=dhcp` unless explicitly set.
- **Internal names:** Caddy LXC (CTID 103) at `192.168.10.201` serves `*.home.arpa` with an internal self-signed CA. Resolution depends on Unbound host overrides on Sentry Gate plus Tailscale split DNS.
- **Power schedule:** the Archivist is on-demand — cron shutdown around 23:00, IPMI wake from Sentry Gate around 07:55. Anything intermittent needs to be observed across that boundary before it's called fixed.

---

## Finding 1 — IPv6 blackhole affecting Node.js-based services

**Observed on:** Seerr (CTID 109). Suspected to affect other containers; not yet surveyed.

### The condition

Containers come up with **link-local IPv6 only** — `fe80::/64` on `eth0`, no global address, no v6 route:

```
2: eth0@if21: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
    inet6 fe80::be24:11ff:fe72:8af1/64 scope link
```

Meanwhile the resolver returns **AAAA records** for external hosts. `getent hosts api.themoviedb.org` returned eight `2600:9000:...` addresses and nothing else. Every one of them is unroutable from inside the container.

### Why it breaks Node specifically

Since Node 17, `dns.lookup` defaults to `verbatim: true` — it uses resolver-returned order rather than sorting IPv4 first. A Node app therefore opens a socket to an unreachable v6 address and blocks until its own client timeout expires, typically 10s.

`curl` does not reproduce this. Happy Eyeballs races A and AAAA in parallel and falls back to IPv4 in milliseconds. **A passing `curl` is not evidence the container's network is healthy for Node workloads** — this is the main thing that makes the fault hard to spot.

Working `curl` output from the affected container, taken while the app was actively failing:

```
code=401 dns=0.021500 conn=0.033471 total=0.130205
code=401 dns=0.002993 conn=0.017102 total=0.108061
code=401 dns=0.002315 conn=0.016824 total=0.104747
```

(`401` is expected and healthy for an unauthenticated TMDB request — it proves DNS, TCP, and TLS all completed.)

### How it presented

Seerr's home route rendered fine. Every other route returned **HTTP 500**. Home is served from local request/media state; Discover, movie detail, and search are server-rendered against the TMDB API, so they failed.

Log signature — note the errors terminate with a bare colon, no HTTP status and no upstream message, which indicates a connect/DNS failure rather than an API rejection:

```
[error][Radarr]: [Radarr] Failed to retrieve profiles: timeout of 10000ms exceeded
[debug][API]: Something went wrong retrieving movie {"errorMessage":"[TMDB] Failed to fetch movie details: "}
[debug][API]: Something went wrong retrieving popular movies {"errorMessage":"[TMDB] Failed to fetch discover movies: "}
[debug][API]: Something went wrong retrieving popular series {"errorMessage":"[TMDB] Failed to fetch discover TV: "}
```

Failures were **intermittent**, not total — a request submitted at 17:58 succeeded in reaching TMDB; failures began at 18:05. That intermittency is consistent with which address family got picked per lookup, and it's why the fault initially looked like load or resource exhaustion.

Disk, SQLite, and memory were all ruled out before DNS: container root was 25% used with 8.4G free, no `SQLITE_*` errors, no OOM kills.

### Remediation applied to Seerr

`/etc/seerr/seerr.conf` ships with `FORCE_IPV4_FIRST=true` present but commented out. Uncommenting it and restarting the service resolved both the TMDB failures and the Radarr profile timeout. It's read via `EnvironmentFile` so it requires a service restart rather than a reload, and it survives helper-script updates because the update path preserves that file.

The Radarr timeout clearing alongside the TMDB errors suggests both shared the same root cause.

### Scope not yet established

Seerr is the only container confirmed affected. Every other helper-script container on this host was built the same way and is presumed to have the same link-local-only v6 config. Candidates worth surveying: Radarr, Sonarr, Prowlarr, qBittorrent, Jellyfin, Caddy (CTID 103; CTID 200 is Vaultwarden).

Most of these are .NET or Go rather than Node and may not exhibit the same address-family preference, so the presence of the underlying condition doesn't automatically mean the same symptom. The distinguishing signature is a ~10s timeout against an external or hostname-addressed endpoint where `curl` from the same container succeeds instantly.

`FORCE_IPV4_FIRST` is a Seerr-specific knob. There is no equivalent per-app setting for most of the others — the general levers are disabling IPv6 at the container level or stopping the resolver from returning AAAA for these lookups.

---

## Finding 2 — containers resolve against the wrong nameserver

Unaddressed as of this writing. Surfaced during the Finding 1 investigation and deliberately left alone so the two changes wouldn't be confounded.

`/etc/resolv.conf` inside CTID 109:

```
# --- BEGIN PVE ---
search lan
nameserver 192.168.1.1
# --- END PVE ---
```

The container is pointed at the **family router**, not Sentry Gate's Unbound at `192.168.10.1`.

Consequences:

- DNSSEC validation, full recursion, and Unbound's blocklists are all bypassed for anything inside that container. The DNS hardening work on Sentry Gate doesn't apply to the container fleet at all.
- `*.home.arpa` will not resolve from inside these containers, since those host overrides live in Unbound. This becomes load-bearing the moment any container needs to reach another by its internal name rather than raw IP — putting Seerr behind Caddy, or configuring inter-service URLs by hostname.
- The `search lan` domain comes from the family router's DHCP, not from anything in this project's design.
- It may also be the source of the AAAA-only responses in Finding 1, though that hasn't been tested.

The `# --- BEGIN PVE ---` markers matter: Proxmox owns this file and rewrites it from container config. Editing it in place inside the container does not persist. It's driven by the container's DHCP lease or by nameserver values set on the container object itself.

Correction (2026-09-18): the Archivist host (`.202`) and Jellyfin were both already static. Jellyfin's `.137` was inside Sentry's dnsmasq pool (`.100–.200`) and has been moved to `.207`. The `192.168.1.1` resolver was **inherited from the host's own `/etc/resolv.conf`**, not from DHCP.

---

## Useful diagnostic signatures

For identifying this class of fault on another container:

```
pct exec <CTID> -- ip -6 addr show eth0          # link-local only, no global scope address
pct exec <CTID> -- getent hosts <external-host>  # AAAA-only response
pct exec <CTID> -- getent ahosts <external-host> # shows whether A records exist at all
pct exec <CTID> -- cat /etc/resolv.conf          # which nameserver is actually in use
```

Timing probe — the `dns=` and `conn=` fields are what matter, not the status code:

```
pct exec <CTID> -- curl -sS -o /dev/null \
  -w 'code=%{http_code} dns=%{time_namelookup} conn=%{time_connect} total=%{time_total}\n' \
  https://<endpoint>
```

Bear in mind this probe **will pass on an affected container**. It is useful for ruling out a total network failure and for reading resolution latency, not for confirming health.

---

## Notes carried in from prior sessions

Relevant to anyone working these containers:

- Unprivileged LXC UID mapping offset is `100000`. Host-side files need matching ownership before a container sees them as usable.
- Verify bind-mount paths with `pct config <CTID>` before troubleshooting permissions — a `chown` against a path that doesn't match the `mpX:` line silently does nothing. This has cost real time once already.
- `/etc/pve` exists only on the Proxmox host. `ls /etc/pve` is the fast check for which shell you're actually in.
- The arr stack shares a single filesystem mount so imports hardlink rather than copy. `ls -li` comparing the torrent file and its library counterpart should show identical inode numbers; differing inodes mean copy-mode imports, which matters on a ~953GB RAID-1 mirror.
- The nightly power cycle means anything intermittent should be re-observed after a full down/up before it's considered closed.
