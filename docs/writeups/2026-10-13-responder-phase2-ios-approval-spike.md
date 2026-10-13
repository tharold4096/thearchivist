# Responder Phase 2 — iOS ntfy approval-button spike

**Date:** 2026-10-13
**Machine(s):** CT 116 responder (192.168.10.216), CT 102 ntfy, sentrygate (read-only), iPhone
**Status:** Complete. The test is torn down. The OPNsense rule and the ntfy user remain for Phase 3.
**Tags:** responder, ntfy, iOS, firewall, automation

---

## Why I built this

* The responder's whole approval model assumes that tapping an ntfy **`http` action** button on the
  iPhone sends a request to CT 116. It was the riskiest unproven assumption, so I tested it before
  writing any service code.

## How I built it

* **Tools/stack:**
  * ntfy `http` actions (`Actions:` header; POST is the default method);
  * a throwaway Python `http.server` listener run as a transient systemd unit
    (`systemd-run --uid=responder -p RuntimeMaxSec=3h`);
  * OPNsense Tailscale-interface rule.
* **Key steps:**
  * Took `pct snapshot 116 pre-phase2`.
  * Created a dedicated ntfy user `responder`, write-only on the alerts topic. The token went straight
    from CT 102 into `~responder/.config/responder/ntfy.env` (`600`) on CT 116 without
    being printed.
  * Started a listener on `192.168.10.216:8787` that logged the method, path, source, the `X-Spike` header
    and the body, and returned 200.
  * Added an OPNsense rule (by hand in the GUI): Tailscale, TCP, iPhone tailnet IP →
    `192.168.10.216:8787`.
  * Published a push with Approve and Deny `http` actions, each carrying a distinct header and body.
* **Config/scripts:** none kept. The listener was deleted after the test.

## What broke

* **Issue: buttons stay live after a decision.**
  Symptom: after tapping Approve, the notification stayed and both buttons kept working (taps
  repeated by hand all reached the listener).
  Root cause: iOS ignores `clear=true` on `http` actions.
  Fix: a server-side guard in the Phase 3 design. Each job is a state machine, and the first tap claims it
  atomically in SQLite (`UPDATE … WHERE state='pending'`, then check that rowcount is 1). Every later or concurrent tap
  returns `already handled` and is logged, with no re-execution and no new diagnosis session.
* **Issue: phone-side cleanup made things worse.**
  Symptom: republishing with the same `X-Sequence-ID` added a **second** notification instead of
  replacing the first. `DELETE /<topic>/<seq>` showed up on the phone as a **blank push**.
  Root cause: the iOS app doesn't apply ntfy's update and delete events. The server accepted both (200,
  `message_delete` event).
  Fix: dropped. Decided notifications stay with dead buttons, and the server guard makes them harmless.
* **Issue: the shell quoting broke the first listener file.** Nested `bash -c` quoting mangled an
  f-string. Fix: wrote the file locally and piped it in on stdin.

## What worked

* **iOS `http` actions work.** Both buttons arrived as `POST` with the configured header and body.
  The UA was `ntfy/9 CFNetwork/3860.700.2 Darwin/25.6.0`. 14 requests were logged in total.
* Source IP was `192.168.10.1` for every tap. Sentry SNATs subnet-routed tailnet traffic, so the
  responder can't tell callers apart by IP. The single-use approval token is the control.
* Teardown: unit `inactive`, script removed, `ss -ltn` shows nothing on 8787.

## What I'd do differently

* Read the firewall counters, not just the rule list, before calling a rule tested. The new rule was
  correct but showed **0 evaluations**. A broader pass rule higher on the Tailscale interface
  (the whole tailnet range → any) matched first, which also leaves the family Jellyfin-only rule unreachable.
  A staged fix was proposed: admin alias first, a DNS-to-Sentry pass, then narrowing the broad rule. It's
  pending a decision; Sentry is edited only by hand.

---

## Resume-ready summary

* Ran a de-risking spike for a human-in-the-loop remediation system. I proved iOS push-notification
  action buttons can reach an internal service over a Tailscale subnet route. I found that the platform
  can't retract or disable buttons, and moved the guarantee against double execution into an
  atomic server-side state claim. Reading the firewall counters also exposed a broad tailnet rule
  that was overriding narrower per-device rules.
