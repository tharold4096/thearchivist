# Site

The source for <https://tharold4096.github.io/thearchivist/>: an Astro static site with the lab topology, a page per host, and every writeup rendered in place.

## Run it

```sh
cd site
npm ci
npm run dev       # live preview at http://localhost:4321/thearchivist/
npm run build     # writes dist/ and scans it for secrets
```

Needs Node 22.23 or newer. Every dependency is pinned to an exact version in `package.json`; fonts are bundled, so the pages load nothing from a CDN.

## Where the content comes from

Nothing is written by hand in here. The build reads the rest of the repo:

| Source | Becomes |
|---|---|
| `hosts/inventory.yml` | The topology, host pages, addresses, ports, dependencies |
| `hosts/<group>/<slug>/README.md` | The hand-written parts of each host page and its known issues |
| `docs/**/*.md` with front matter | Writeups, filters, the open follow-ups list |
| `journal/responder/**` | Responder journal records |

To change what the site says, edit those files and push to `main`. The workflow in `.github/workflows/pages.yml` rebuilds and deploys.

## Guard rails

- **Only git-tracked files are read.** `src/lib/repo.ts` lists files with `git ls-files`, so anything `.gitignore` keeps local (the arr stack) cannot reach the build, even on a machine where those files exist. If a path on the deny list is ever tracked, the build stops.
- **The output is scanned before deploy.** `scripts/check-output.mjs` fails the build on ntfy tokens, real ntfy topic names, private keys, or local-only paths. `<SET-ON-HOST>` placeholders are expected and shown as text.
- **Links to unpublished files are dropped.** A markdown link whose target git does not track renders as plain text.

## Status

Host status is a snapshot: the `status` of each host in the inventory, observed on the inventory's `verified` date. It all flows through `loadStatus()` in `src/lib/inventory.ts`. If a tracked `status.json` appears at the repo root, it takes over without other changes:

```json
{ "as_of": "2026-12-01", "live": true, "hosts": { "ct100-jellyfin": "running" } }
```

The site also publishes the snapshot it was built from at `/status.json`, and every status badge carries `data-status-host="<slug>"`.
