---
title: <package/platform> <from> → <to> on <hosts>
date: YYYY-MM-DD
type: update
status: complete
hosts: []
tags: [patching]
summary: >-
  Updated X from version A to B on N hosts; result in one clause.
verified: YYYY-MM-DD
open: 0
---

# <Title>

## At a glance

| | |
|---|---|
| **Scope** | Which hosts, which packages |
| **Versions** | from → to |
| **Method** | `homelab-update` / manual apt / in-app updater / pveupgrade |
| **Safety net** | Snapshot `<name>` / vzdump / none (why) |
| **Downtime** | Reboot needed? How long? |
| **Result** | Clean / partial / rolled back |

## Context

Why now: routine cycle, a CVE, a Wazuh finding, a feature you need.

## Before

| Host | Package | Version |
|---|---|---|
| | | |

## What was run

```sh
commands, in order
```

## After

| Host | Package | Version | Service healthy? |
|---|---|---|---|
| | | | |

## What broke

One entry per problem. Skip the section if nothing did.

- **Symptom:**
- **Cause:**
- **Fix:**

## Rollback

How to get back: snapshot name, `pct rollback`, pinned package version.

## Follow-ups

- [ ] Remove the pre-update snapshot after N days: `pct delsnapshot <id> <name>`
