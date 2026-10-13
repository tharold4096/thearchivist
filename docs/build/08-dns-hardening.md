# DNS Hardening — Unbound Configuration

## Overview
_What does this component control, and what's the scope boundary — why does this apply to the server segment and deliberately not the whole household?_

## What I Configured
- DNSSEC validation status: _[...]_
- Recursion vs forwarding decision: _[...]_
- WAN DHCP override setting: _[...]_
- Port 53 redirection status: _[...]_

## Why I Made This Choice
_Why is DNSSEC the actual security control here while everything else is "just" privacy — what's the practical difference in what each one protects against? Why full recursion over DoT forwarding, given the self-hosting pattern elsewhere in this build? Why does the WAN DHCP override checkbox matter, and what would happen silently if you left it on?_

## How I Did It
_Document the actual Unbound configuration steps, and how you verified DNSSEC and recursion were actually working rather than just configured._

## Problems I Ran Into
_Anything that didn't take effect the way you expected on the first pass? Any conflicts between this config and DHCP-assigned settings elsewhere?_

## What I'd Do Differently
_Is there anything about the DoH gap you'd want to address differently, even knowing it's an acknowledged limitation rather than a fixable one? Would you reconsider the recursion-vs-forwarding tradeoff for any part of the network?_

## Skills This Demonstrates
_e.g. DNS security fundamentals (DNSSEC, cache poisoning), understanding the difference between configuring a resolver and controlling a network segment's resolution path, honest documentation of a known limitation rather than glossing over it._

## Evidence
_Unbound config screenshots, a DNSSEC validation test result, dig/drill output showing the resolver working end to end._
