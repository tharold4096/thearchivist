---
title: <symptom in plain words>
date: YYYY-MM-DD
type: incident
status: complete           # complete = root cause known AND fix verified
hosts: []
tags: []
summary: >-
  <Symptom> was caused by <root cause>; fixed by <fix>.
verified: YYYY-MM-DD
open: 0
---

# <Title>

## At a glance

| | |
|---|---|
| **Symptom** | What a user or alert saw |
| **Impact** | What was down, for how long |
| **Root cause** | One sentence |
| **Fix** | One sentence |
| **Prevention** | What stops it recurring (or "none yet") |
| **Detected by** | Checkmk / Wazuh / responder / a person noticed |

## Timeline

| Time | Event |
|---|---|
| HH:MM | First symptom |
| HH:MM | Fix applied |

## Diagnosis

The tree you walked. One line per hypothesis, including the wrong ones, and the evidence that ruled each in or out:

| Hypothesis | Test | Result |
|---|---|---|
| | | ruled out / confirmed |

## Root cause

The mechanism in a paragraph: why it happened, not only what.

## Fix

```sh
what was run
```

## Verification

```text
output that proves the fix held
```

## Prevention

What changed so it doesn't come back (watchdog, alert, config). Link the change or build doc.

## Follow-ups

- [ ] Open items, each with the command that closes it.

## Lessons

Optional. What you would check first next time.
