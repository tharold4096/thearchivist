# Phase 3 brief: homelab website (GitHub Pages)

Written 2026-11-12 at the end of phases 1–2 (Opus 5.5). Read this before building. `.claude/` is gitignored, so this file stays local.

## What the user asked for

> Create a fully functional, interactive website for managing the layout and reading writeups and updates for the homelab. Click into different hosts, see IP addresses and ports plainly, see the overall network topology when you click out, and check status (if possible). Smooth, easy to use, effective.

After the site comes **phase 4**: rewrite the root `README.md` into a comprehensive, engaging, resume-ready summary and outline of the repo. Do it only once the site is done.

The user will set up GitHub Pages first. Ask which source they chose (branch `/docs`, `gh-pages`, or a GitHub Actions deploy) before you pick a build approach.

## Data you already have (don't re-scrape)

| Source | What it holds |
|---|---|
| `hosts/inventory.yml` | 19 public hosts and 4 networks: IPs, ports (port/proto/service/bind/via), roles, resources, `runs_on`, `depends_on`, monitoring, backup, Caddy routes on ct103, storage on thearchivist, interfaces on sentrygate/thearchivist. Schema comments at the top. |
| `docs/**/*.md` front matter | `title, date, type (build/change/update/incident/host/reference), status, hosts[], tags[], summary, verified, open` on 41 public docs |
| `hosts/<group>/<slug>/README.md` | Host pages generated from the inventory; same front matter (`type: host`) |
| `docs/writeups/README.md`, `hosts/README.md` | Indexes, useful as sanity checks for counts |
| `journal/responder/` | Auto-published responder incident records (dated md) |

Topology edges come from `runs_on` (containment), `depends_on` (service dependency), each host's `networks`/`interfaces`, and the Caddy `routes` (proxy edges).

## Hard constraints

1. **Arr stack never reaches the site.** Don't read `hosts/inventory.arr-stack.yml`, the `hosts/lxc/ct109-…ct114-*` dirs, `hosts/lxc/arr-stack/`, or any gitignored doc. Build only from git-tracked files (`git ls-files`), so the build can't see them even locally. Some public docs mention arr apps in passing; that's pre-existing and acceptable.
2. **The site is public.** It will show RFC1918 IPs and ports. The user asked for that explicitly, and the repo already holds the same data, but say it once in a line before publishing. Never show secrets. Grep the built output for `tk_`, `homelab-alerts-`, `<SET-ON-HOST>` handling and `BEGIN .* PRIVATE`.
3. **Live status is the hard part.** A public HTTPS Pages site can't poll `192.168.10.x`: mixed-content and Private Network Access rules block it, and the lab is powered off 23:00–07:45 every night. Options, best first:
   - **(recommended)** A small job in the lab, most naturally on CT 116, which already pushes the responder journal to this repo. It reads Checkmk's state (the `responder-ro` user exists) and commits `status.json` every N minutes. The site shows it with a "last updated" stamp and greys out when stale. The tradeoff: it publishes up/down state publicly, and it adds commits to the repo. It could go to a separate branch.
   - Client-side probes that work only when the viewer is on the tailnet (fetch to `https://*.home.arpa`, which needs the Caddy internal CA trusted). Fragile; only an optional extra.
   - Static only, showing the `status` observed at `verified`. This is the honest floor.
   Present these as choices to the user. Don't decide alone.
4. **CDN and version rules** for any scripts: pin exact versions.

## Design cues from the user's profile

Brand: Spartan/Lambda motif, burnt orange / spartan red / dark iron, monospace numerals. They chose a tap-first dashboard over keyboard-first in the past. Don't assume a terminal aesthetic. Use light and dark themes.

Must-haves from the ask: host drill-down (IPs and ports plainly), a topology view as the "zoomed-out" home, writeups and updates readable in-site (render markdown), status, smooth navigation. Nice-to-haves that the data supports: filter writeups by type/host/tag/status, an open-follow-ups view (`open > 0`), search, a timeline.

## Repo facts

- Branch `repo-reorg`. PR #3 (Checkmk rollout, responder, repo reorganisation) is still OPEN against `main`.
- Phases 1–2 are **staged, not committed** as of 2026-11-12, unless the user committed after this was written. Check `git status`.
- Front-matter dates are ISO. `verified` means checked live on that date, not edited on that date.
