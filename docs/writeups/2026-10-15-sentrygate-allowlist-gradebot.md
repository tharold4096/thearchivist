# Sentry Gate DNSBL: Allowlist for CSCE 3550 Gradebot

**Date:** 2026-10-15
**Machine(s):** Sentry Gate (OPNsense, Unbound DNSBL); observed from Omarchy (laptop)
**Status:** Complete
**Tags:** DNS, DNSBL, Unbound, allowlist, accountability, coursework

\---

## Why I did this

* The CSCE 3550 Project 2 grading client (`gradebot project-2`) reports results to
  `https://gradebot-unt-fab5dc5c.koyeb.app`. Its "Quality" check failed with
  `dial tcp 0.0.0.0:443: connect: connection refused`, which cost 5 points on an otherwise passing run.
* Omarchy can only resolve through Sentry (`100.116.54.77`, pinned by the 2026-09-26 DNS lock), so the
  fix had to be made on Sentry, not on the laptop.

## How I did it

* **Where:** OPNsense → Services → Unbound DNS → Blocklist → Allowlist Domains. _[confirm the exact menu labels for your OPNsense version]_
* **Entry:** `gradebot-unt-fab5dc5c.koyeb.app`. _[confirm: this exact hostname only, not `koyeb.app`]_
  Only the one host the course uses is allowed. Free PaaS domains like Koyeb get blocklisted because
  attackers use them for phishing and payload hosting, and allowing the whole domain would undo that.
* **Applied**, then `resolvectl flush-caches` on Omarchy to drop the cached `0.0.0.0` answer.
* **Rollback:** remove the entry from Allowlist Domains and Apply.

## What broke

* **Issue: gradebot Quality check couldn't reach its server**
  Symptom: `dial tcp 0.0.0.0:443` in the gradebot output.
  Root cause: `getent hosts gradebot-unt-fab5dc5c.koyeb.app` on Omarchy returned `0.0.0.0`, which is
  the answer the Unbound DNSBL gives for a blocked name (the same answer as the `instagram.com` canary).
  Direct queries to 1.1.1.1 were refused by `sentry_dns_lock`, as designed, so no other resolver was
  available to check against. _[note which blocklist matched, if you checked]_
  Fix: the allowlist entry above.

## Verification

* After Apply and the cache flush, `getent hosts gradebot-unt-fab5dc5c.koyeb.app` returns real
  addresses (`prod-glb.koyeb.app.cdn.cloudflare.net`, e.g. `2606:4700:10::ac42:acae`).
* gradebot `project-2` Quality row: _[record the result of the rerun]_

## Accountability

* Adding to the allowlist is a governed change, so `dnsaudit attest` pushes an alert on the first run
  that sees it. That's intended, and this writeup is the explanation for it. _[record when the alert fired]_
* No `EXEMPT_REMOVALS`-style exemption was added; the entry stays visible as a standing allowlist addition.

## Tradeoff

* This allowlists one specific host instead of a category. Each later project that uses a different
  gradebot URL will need its own entry, and its own alert. That's intended: each exception stays
  explicit and has a written reason.
