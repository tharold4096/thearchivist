# Remote Access — Mesh VPN and Firewall Rule Hardening

## Overview
_What problem does this solve, and what constraint (housing policy) made the usual answer — port forwarding — unavailable to you?_

## What I Configured
- Devices enrolled on the tailnet: _[...]_
- Subnet route advertised: _[...]_
- Firewall rule source: _[...]_ (alias name, contents)
- Interface assignment: _[...]_

## Why I Made This Choice
_Why is an outbound-only mesh VPN compatible with a housing policy that bans routers, when port forwarding wouldn't be? Why verify from cellular data specifically rather than trusting a test on home WiFi? Why move from an any/any pass rule to an explicit host allowlist — what's the actual risk of leaving it broad?_

## How I Did It
_Document the two non-obvious blockers you hit: the plugin not auto-assigning its interface, and the alias/rule debugging process. Walk through how you used the live firewall log to narrow down the cause rather than guessing._

## Problems I Ran Into
_The rule that looked completely correct but silently dropped everything — what did you check, in what order, and what did the live log entry actually tell you versus what it ruled out? Be specific about the alias table vs the alias edit form distinction, since that's the actual lesson._

## What I'd Do Differently
_Would you check the alias's resolved contents earlier in the process next time, before assuming the rule itself was wrong? Anything about the sequencing (interface assignment before rule creation) you'd flag for your future self?_

## Skills This Demonstrates
_e.g. zero-trust/outbound-only remote access design, default-deny firewall philosophy, systematic log-based debugging, least-privilege access control via aliases._

## Evidence
_Firewall rule screenshot, alias configuration, the live log entry that cracked the debugging session._
