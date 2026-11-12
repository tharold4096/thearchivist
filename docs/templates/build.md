---
title: <what was built>
date: YYYY-MM-DD
type: build
status: complete
hosts: []
tags: []
summary: >-
  Built X on Y to solve Z; it now does W.
verified: YYYY-MM-DD
open: 0
---

# <Title>

## At a glance

| | |
|---|---|
| **Goal** | The problem or capability, in one clause |
| **Stack** | Tools and where they run |
| **Hosts** | slug (IP) |
| **Entry points** | URL, port, timer, or command |
| **Result** | What it does now, with a number if you have one |
| **Config** | Repo path(s) |

## Context

What gap this fills and why it was worth the time: a real risk, a skill, or a piece of the bigger lab.

## Design

How the parts fit together, and the alternatives you turned down and why. A small diagram earns its place here:

```text
source ──► component ──► sink
```

## What was built

The key steps, as a list. Link configs in `hosts/` rather than pasting them.

1. …

**Config/scripts:** [`hosts/<group>/<slug>/`](../../../hosts/)

## Issues hit

One entry per problem:

- **Symptom:**
  **Cause:**
  **Fix:**

## Verification

The evidence: alerts that fired, a restore that worked, uptime over N days. Real output, not "it works".

## Follow-ups

- [ ] Open items, each with the command that closes it.

## Lessons

Optional. What you would do differently.

## Resume line

- Action verb + what + measurable result (e.g. "Deployed Checkmk across 17 hosts with dependency-aware alerting, cutting duplicate pages per outage from N to 1").
