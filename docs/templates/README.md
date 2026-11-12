# Writeup templates

Every document in this repo starts the same way: **YAML front matter**, then an **At a glance** table. A reader can learn what a doc is, what it touched and whether it is finished in about ten seconds, without reading any prose. The website reads the front matter to build its index, host pages and timeline. A doc without front matter does not show up there.

## Pick a template

| You are writing about… | Template | Lives in | Example |
|---|---|---|---|
| A machine: what it is, its IP, ports, configs, history | [`host.md`](host.md) | `hosts/<group>/<slug>/README.md` | `hosts/lxc/ct116-responder/README.md` |
| A deliberate config edit to something that already exists | [`change.md`](change.md) | `docs/writeups/changes/` | Removing the qBittorrent upload cap |
| Patching, upgrading or migrating software versions | [`update.md`](update.md) | `docs/writeups/updates/` | The weekly `homelab-update` run picking up a kernel |
| Something broke, or looked broken, and you diagnosed it | [`incident.md`](incident.md) | `docs/writeups/incidents/` | WireGuard stall after a Sentry reboot |
| A new service, tool or capability built from scratch | [`build.md`](build.md) | `docs/writeups/builds/` | The responder, Checkmk rollout |
| Background a reader needs but that isn't one piece of work (architecture, hardware baseline, investigation notes) | no fixed body; front matter + headings | `docs/overview/` | Network architecture, R710 hardware |

When a piece of work is two of these (an incident whose fix was a config edit), write it as the one that **started** it (incident) and describe the edit inside it. Don't write two docs.

Filename: `YYYY-MM-DD-short-topic.md`, dated on the day the work happened. Arr-stack docs must contain an arr token in the filename (`sonarr`, `prowlarr`, `arr-stack`, …) so `.gitignore` keeps them local. Check with `git check-ignore -v <file>` before you commit.

## Front matter reference

```yaml
---
title: Checkmk rollout across 17 hosts          # the headline, plain words
date: 2026-10-12                                # when the work happened
type: build                                     # build | change | update | incident | host | reference
status: complete                                # complete | in-progress | planned | blocked | rolled-back | superseded
hosts: [thearchivist, ct115-checkmk]            # slugs from hosts/inventory.yml
tags: [monitoring, checkmk, ntfy]               # lowercase, hyphenated
summary: >-                                     # ONE sentence: what, why, result
  Replaced Netdata with Checkmk on every guest and routed alerts through
  ntfy with parent/child suppression so one outage pages once.
verified: 2026-11-12                            # last date facts were checked against the live box
open: 2                                         # unresolved follow-ups (0 when done)
supersedes: []                                  # filenames this doc replaces, if any
---
```

Rules that keep the index honest:

- `status: complete` means the verification step actually ran and its output is quoted in the doc. "Applied, should work" is `in-progress`.
- `verified` changes only when someone re-checks the live system. Editing the prose doesn't count.
- `open` must equal the number of unticked items in **Follow-ups**.
- Never put a secret, token or ntfy topic name in a doc. Write `<SET-ON-HOST>` and name the host-side file that holds the real value.

## Section vocabulary

The templates reuse the same section names so they read alike:

| Section | Answers |
|---|---|
| **At a glance** | The whole doc in five rows. If someone reads nothing else, this is enough. |
| **Context** | Why this mattered: the problem, risk or goal. |
| **What changed** / **What happened** | The facts: settings, files, commands, timeline. |
| **Verification** | How you know it worked, with real output. |
| **Rollback** | The exact way back if it goes wrong. |
| **Follow-ups** | A checkbox list of what is still open. Each item names the command that would close it. |
| **Lessons** | Optional. Judgment, not narration. |
| **Resume line** | Optional, for build docs. One quantified, action-verb bullet. |
