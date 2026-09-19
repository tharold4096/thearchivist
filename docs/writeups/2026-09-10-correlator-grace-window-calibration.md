# Multi-Target Correlator — Grace Window Calibration

**Date:** 2026-09-10
**Machine(s):** Sentry Gate (OPNsense) — analysis targets Tower and Omarchy
**Status:** Complete (monitoring)
**Tags:** monitoring, correlator, tailscale, healthchecks, false-positives, calibration

---

## Why I built this

The two-signal correlator was running with a 100% false-positive rate on the
Omarchy target. Signal A is a 5-minute Healthchecks.io liveness ping; Signal B
is the Tailscale peer's `Online` field read from Sentry Gate. An event fires
when A says "device is up" and B says "peer is offline" for `grace_polls`
consecutive one-minute polls.

Over the 2026-09-08 to 2026-09-10 window the log held 8 Omarchy events and 6
Tower events. Ground truth: every Tower event was an intentional disconnect,
every Omarchy event was noise. Since `notify` is on for both targets, all 8
Omarchy false positives pushed to the phone. A monitor that is wrong every
time it speaks is worse than no monitor, so the threshold had to be derived
from evidence rather than inherited.

Omarchy's `grace_polls` had been set to 5 as a placeholder — the source
comment said outright that it mirrored Tower's value "because a number was
needed, NOT because 5 was chosen from evidence."

## How I built it

* **Tools/stack:** Python 3.13 on FreeBSD/OPNsense, cron at a 60s cadence,
  Healthchecks.io API, `tailscale status --json`, JSONL event log at
  `/var/log/multi_correlator/events.jsonl`.
* **Key steps:**
  * Pulled the 226-line event log read-only and reconstructed every "target
    episode" (entry into the A-present/B-offline condition through exit) for
    both devices, with the Signal A ping age at each entry.
  * Reconstructed each device's Signal A ping series from every distinct
    `signal_a_last_ping` value in the log, and flagged pings that landed
    off the timer's 5-minute phase — those are the `Persistent=true`
    catch-up pings that fire on resume.
  * Swept candidate `grace_polls` values against both devices' real episode
    length distributions to find a threshold that keeps every true positive
    and drops every artifact.
  * Deployed via staged temp file: backup, upload as `.new`, `py_compile` on
    the host's own interpreter, `chown`/`chmod` to match, then atomic `mv`.
* **Config/scripts:** `../../../omarchy-monitor/correlator2.py` (repo copy now
  byte-identical to the deployed file, md5 `6db1e6d4c39a4d5b0a4e17c98c2da6dd`).
  Host path `/usr/local/opnsense/scripts/multi_correlator/correlator2.py`.
  Backup left on the host as `correlator2.py.bak-20260910-113011`.

## What broke

* **Issue: Grace window shorter than the Signal A staleness window.
  Symptom:** Omarchy events fired 5–7 polls into an episode and then ended
  one or two polls later with `signal_a_detail` reading `stale_by_1s` through
  `stale_by_56s`. Signal A aged out almost immediately after each event was
  confirmed.
  **Root cause:** Signal A is considered present if the last ping is within
  `HC_PING_INTERVAL_SECONDS` (300) + `HC_LIVENESS_GRACE_SECONDS` (120) = 420s.
  The grace window was 5 polls = 300s. Because 300 < 420, a suspend leaves the
  last pre-suspend ping looking fresh for longer than it takes to confirm an
  event. Tailscale marks the peer offline within a poll or two of the suspend,
  so the correlator sees "up but off Tailscale" for the remainder of the
  staleness window. That caps a purely artificial episode at 420/60 = 7 polls,
  which means any threshold of 7 or less sits *inside* the artifact band.
  The evidence is decisive: predicted episode length is
  `(420 - ping_age_at_entry) / 60`, and that model matched 16 of 18 observed
  Omarchy episodes to within one poll.
  **Fix:** Raised the grace window above the staleness window. This is the
  same defect that produced Tower's known shutdown-race false positive — not a
  variant of it. Omarchy just hits it far more often because it suspends
  several times a day and Tower rarely powers off.

* **Issue: Resume catch-up pings sharpen the same race.
  Symptom:** Three of the eight Omarchy events fired within 15 minutes of a
  ping that landed off the timer's 5-minute phase.
  **Root cause:** `omarchy-liveness.timer` uses `OnCalendar` with
  `Persistent=true` specifically so a missed tick fires on resume. That
  catch-up ping restarts the 420-second staleness clock at an arbitrary
  wall-clock moment, often before Tailscale has re-established. The clearest
  case: a catch-up ping at 13:42:31 UTC on 09-10, Tailscale registering the
  peer offline at 13:43, the event confirmed at 13:47, Signal A stale at
  13:50.
  **Fix:** Same threshold change. The catch-up ping is correct behaviour and
  was left alone — it shrinks the post-resume blind window, which is what it
  is there for.

* **Issue: A second, unrelated false-positive class.
  Symptom:** Two Omarchy events ran 17 and 36 polls, well past the 7-poll
  staleness ceiling, with Signal A being refreshed on schedule throughout.
  **Root cause:** Not a staleness artifact. The laptop was awake and pinging
  normally while the Tailscale peer flapped — three offline/online cycles in
  41 minutes on 09-08, consistent with roaming between networks. Tower never
  does this; its true positives hold the peer offline continuously.
  **Fix:** Only a longer window separates this from a real lapse, so Omarchy's
  threshold was set above the longest observed flap burst rather than merely
  above the staleness ceiling.

* **Issue: Repo copy had silently drifted from the deployed script.
  Symptom:** md5 mismatch between `omarchy-monitor/correlator2.py` and the
  file on Sentry Gate.
  **Root cause:** The cutover change (flipping `notify` to `True` on both
  targets) and a later change rendering alert timestamps in
  `America/Chicago` were made on the host and never written back.
  **Fix:** Repo copy resynced to be byte-identical to the deployed file.

* **Issue: The parallel-run comparison never actually ran.
  Symptom:** `compare-parallel-run.py old.jsonl new.jsonl` exits 2 with "the
  two logs do not overlap — nothing was compared."
  **Root cause:** `old.jsonl` was fetched at 2026-09-07 19:43 CDT, before the
  parallel window had accumulated anything. It ends at 2026-09-08T00:21 UTC;
  `new.jsonl` begins at 00:38. The two files never covered the same period.
  **Fix:** None available. `/var/log/tower_correlator` no longer exists on
  Sentry Gate, so the old correlator's records are gone and the comparison
  cannot be reconstructed. Cutover has already happened. Noted here rather
  than fixed — see "What I'd do differently".

## What worked

Episode lengths sorted by device made the calibration failure unambiguous.

Omarchy episodes that did **not** fire ran 1, 1, 1, 1, 1, 2, 2, 2, 3, 4 polls.
Omarchy episodes that **did** fire ran 5, 5, 6, 6, 6, 7, 17, 36 polls.
Tower's four confirmed true positives ran 19, 69, 116, 119 polls. Tower's two
known false positives ran 5 and 5, both exiting to `device_off`.

The threshold of 5 was sitting in the middle of the artifact distribution on
both devices.

New values, applied 2026-09-10 and verified in place:

| Target  | Old | New | Effect on the 2026-09-08..10 log |
|---------|-----|-----|----------------------------------|
| tower   | 5   | 8   | All 4 true positives kept; both 5-poll false positives dropped |
| omarchy | 5   | 40  | All 8 false positives dropped |

8 polls is 480s, which clears the 420s staleness window — the principled floor
that both targets should always have satisfied. 40 polls also clears the
36-poll flap burst with margin, at the cost of 40 minutes of detection latency
on Omarchy. That is the right trade on a roaming laptop: a Tailscale lapse
there only matters if it persists.

Deployment verified: host `py_compile` passed on Python 3.13 before the swap;
both targets were `compliant` with a zero streak and no active event at the
moment of the swap; `poll_count` advanced 3831 → 3834 across it; zero
`correlator_crash`, `notify_error`, or `auth_error` records in the log.

`notify` deliberately left `True` on both targets — the notifications are
being used to observe correlator behaviour and no one else receives them.

## What I'd do differently

* Derive the grace window from the staleness window in code rather than
  hand-setting it. `grace_polls` should never be allowed below
  `ceil(LIVENESS_WINDOW_SECONDS / poll_cadence) + 1`; that invariant would
  have made both devices' false positives structurally impossible from day
  one, instead of requiring 62 hours of evidence to find.
* Fetch both sides of a parallel-run comparison at the *same* moment, at the
  *end* of the window. Fetching the old log first, before the window ran,
  silently guaranteed a non-overlapping comparison — and the failure went
  unnoticed because the cutover proceeded anyway.
* Signal B's `Online` boolean is a weak signal for a roaming laptop.
  `LastSeen` / `LastHandshake` would likely separate the flap class from a
  real disconnect without needing a 40-minute window.

---

## Resume-ready summary

* Diagnosed a 100% false-positive rate in a two-signal device-compliance
  correlator by reconstructing 18 alert episodes and the underlying liveness
  ping series from a 226-record JSONL log; identified a threshold inversion
  (300s confirmation window against a 420s liveness staleness window) that
  made suspend-induced artifacts indistinguishable from real events, and
  derived a predictive model matching 16 of 18 episodes to within one poll.
* Recalibrated per-device alert thresholds from evidence, eliminating all 8
  false positives on the laptop target and both known false positives on the
  desktop target while retaining 100% of confirmed true detections; deployed
  via staged atomic swap with pre-flight syntax validation and post-deploy
  state verification, and resynced a drifted configuration back to version
  control.
