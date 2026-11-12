---
title: <verb> <thing> on <host>
date: YYYY-MM-DD
type: change
status: complete
hosts: []
tags: []
summary: >-
  Changed X from A to B so that C.
verified: YYYY-MM-DD
open: 0
---

# <Title>

## At a glance

| | |
|---|---|
| **What** | The setting or file that changed, before → after |
| **Why** | The problem it solves, in one clause |
| **Where** | host · path |
| **Risk** | What could break, and who would notice |
| **Rollback** | One command, or "restore `<file>.bak`" |
| **Verified** | The check that proved it, and when |

## Context

Why this edit was needed now. Link the incident or build that led to it, if there is one.

## What changed

| Setting / file | Before | After |
|---|---|---|
| `path` `key` | old | new |

Steps, as commands. Point to the repo copy of any config instead of pasting long files:

```sh
# on <host>
cp /etc/x /etc/x.bak.YYYYMMDD
...
```

**Repo copy:** [`hosts/<group>/<slug>/<file>`](../../../hosts/)

## Verification

```text
command you ran
the output that proved it
```

## Rollback

```sh
exact commands to undo
```

## Follow-ups

- [ ] Anything still open, with the command that closes it.

## Tradeoff

Optional. What this edit gave up, if anything.
