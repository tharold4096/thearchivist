---
title: "Responder: build, deploy and first live remediation"
date: 2026-10-13
type: build
status: complete
hosts: [ct116-responder, ct115-checkmk, ct102-ntfy, ct100-jellyfin]
tags: [automation, claude, checkmk, ntfy, incident-response, security]
summary: "Built an alert responder that has Claude diagnose Checkmk alerts inside a locked-down container and proposes a fix I approve with one tap on my phone; first live run restarted a stopped Jellyfin."
verified: 2026-11-12
open: 4
---

# Responder: build, deploy, and first live remediation

## At a glance

| | |
|---|---|
| **Goal** | Diagnose major alerts automatically and fix them with one-tap approval |
| **Stack** | Python service on CT 116, headless Claude Code, Checkmk notification plugin, ntfy action buttons, `rgate` command gate, nftables |
| **Hosts** | ct116-responder (192.168.10.216:8787) ← ct115-checkmk; → ct102-ntfy |
| **Entry points** | `responder.service`; approval URLs on :8787 over Tailscale |
| **Result** | Live end-to-end run passed: alert → diagnosis → approval → fix → verify |
| **Config** | hosts/lxc/ct116-responder/ |

> **Current state (verified 2026-11-12):** `responder.service` active; every deployed Python file in `/opt/responder` matches the repo. The repo reorganisation it mentions is still open as PR #3 (`repo-reorg`).

## Context

* Checkmk alerts reached my phone, but every fix still meant opening a laptop. I wanted a
  responder that diagnoses major alerts on its own and proposes a fix I can approve with one tap.
  It had to stay safe when alert text is attacker-influenced, and it had to stop asking about
  fixes I've already approved.

## What was built

* **Tools/stack:** Python standard library only (HTTP server, `sqlite3`), headless Claude Code
  2.1.296, OpenSSH forced commands, ntfy `http` actions, Checkmk notification plugins, git.
* **Key steps:**
  * Claude runs as its own `rclaude` user through the root-owned `run-claude`. Only `Bash` is
    available, only `gate-read`/`cmk-read` are allowed, and `dontAsk` denies everything else. Its SSH key is pinned on the
    target to `rgate read`, so the target refuses a write even if the wrapper is bypassed.
  * Job state is in SQLite. Every transition is a guarded `UPDATE … WHERE state=…`, so double taps,
    replays and concurrent executors can't both win. This was tested with 20-thread races and a mutation
    test that deliberately removed the guard.
  * Learned approvals: an exact `(host, verb, unit)` approved once auto-runs next time. The limits are
    2 per action per 24h and 4 per hour overall. A failed verification demotes the action, and a Revoke button comes with every auto-run push. Security services
    and Vaultwarden are protected and never remembered.
  * Checkmk has a new `responder` rule, cloned from the ntfy rule, which stays in place as the fallback.
    `cmk-read` uses a guest-role automation user.
  * Journal: every outcome is pushed as a scrubbed summary to `journal/responder/` on `main` with a
    deploy key that is limited to this repo. Transcripts stay on CT 116, and arr-stack hosts are never published.
* **Config/scripts:** [`hosts/lxc/ct116-responder/`](../../../hosts/lxc/ct116-responder), and its README covers the trust
  boundary and the rebuild checklist. Plugin: [`hosts/lxc/ct115-checkmk/responder-notify.py`](../../../hosts/lxc/ct115-checkmk/responder-notify.py).

## Issues hit

* **Issue: service crashed on start.**
  Symptom: `ModuleNotFoundError: No module named 'diagnose'`.
  Root cause: `python3 -I` also removes the script's own directory from `sys.path`.
  Fix: `-E -s`, which still ignores `PYTHON*` env and user site-packages.
* **Issue: second journal record never reached GitHub.**
  Symptom: `journal push gave up after retries`. The clone was "ahead 3, behind 1".
  Root cause: I merged PR #4 two seconds before the push, so `main` moved. Rebasing in a depth-1
  clone has no merge base, so every retry failed.
  Fix: no more rebasing. Records go to an on-disk queue. A flush resets to `origin/main`, re-applies the
  queue, pushes, and clears the queue only after success. The stuck record was recovered from the local
  commit and published. There's now a test where `main` moves between records.
* **Issue: `rgate logs` logged `rc=141`.**
  Root cause: the 16 KB output cap closes the pipe early (SIGPIPE).
  Fix: treat 141 as truncation, not failure.
* **Issue: Claude Code wasn't allowed to stop Jellyfin for the test** (auto-mode classifier,
  "interfere with workloads"). I ran the stop myself.

## Verification

* **Live run, 2026-10-13:**
  * 18:17:20: HTTPS check CRIT (502). Both Checkmk rules fired.
  * 18:17:30: Claude, using read-only `status` and `logs`, diagnosed "stopped (inactive/dead), normal systemd stop, no crash". It
    proposed `restart jellyfin.service` with high confidence. The push arrived.
  * 18:19:14: Approve tap (through Sentry). The restart ran with the executor's full-mode key.
  * 18:19:33: verified (systemd active and `/health` = `Healthy`) in 19 s. The grant was recorded. 18:20:20: Checkmk RECOVERY.
* Security checks before going live:
  * Claude's key was refused `restart` on CT 100 even through raw SSH.
  * `cat /etc/hostname` was denied by the permission layer.
  * An injected "run id, print the token, propose a restart" alert was detected and ignored.
  * A wrong bearer token got 403. A non-allowed LAN source was dropped by nftables.
* 31 unit tests: store, grants, and journal against a real bare repo.

## Follow-ups

Status as of 2026-11-12. Ticked items are closed; the evidence is in *Current state* above or the linked doc.

- [ ] Prove the auto-run path: a second Jellyfin stop, then the Revoke button.
- [ ] Phase 7 acceptance tests: deny, expiry, replayed URL, outage with the responder stopped.
- [ ] Phase 1b: extend `rgate` to more containers.
- [ ] Phase 8: daily Wazuh digest.

## Lessons

* Don't use `--depth 1` with rebase for an automated committer. Make it reset-and-replay from the
  start.
* Open items:
  * prove the auto-run path, with a second Jellyfin stop and its Revoke button;
  * the Phase 7 acceptance tests: deny, expiry, replayed URL, and an outage with the responder stopped;
  * Phase 1b, which extends rgate to more containers;
  * Phase 8, the daily Wazuh digest.

---

## Resume line

* Built an LLM-assisted incident responder for a Proxmox homelab. Checkmk alerts trigger a
  sandboxed, read-only Claude diagnosis, and remediation is gated by a one-tap phone approval executed by
  deterministic code. I enforced the trust boundary on the targets with SSH forced commands and
  per-key read/write modes, made double execution impossible with atomic state transitions, and
  published an audit trail of every incident to git. The first live outage went from alert to verified fix in about
  2 minutes, including the human approval.
