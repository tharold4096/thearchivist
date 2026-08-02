# WAN/LAN Interface Split and Addressing

## Overview
_What did the network topology look like before this step, and what does it look like after? What does "inline" actually mean in practice, and what changed physically to make it true?_

## What I Configured
- WAN interface / addressing method: _[...]_
- LAN interface / static address / subnet: _[...]_
- DHCP server status on LAN: _[...]_
- Addressing plan (family LAN, WAN, LAN, mesh overlay): _[...]_

## Why I Made This Choice
_Why does WAN plug into the router rather than the modem? Why is double NAT acceptable here when it's normally something to avoid? Why must "Block RFC1918 Private Networks" stay off, and what would the symptom have looked like if you'd left it on? Why did the DHCP-on-LAN answer change from your original plan once the topology was actually segmented?_

## How I Did It
_Document the console-driven process — the exact prompt sequence, and the order you did things in (WAN before LAN, and why that order mattered for getting connectivity back fastest)._

## Problems I Ran Into
_The accidental mid-reconfiguration lockout is worth documenting honestly here — what happened, why Tailscale went down as a downstream symptom rather than a separate failure, and how you diagnosed that it was a routing problem and not a VPN problem._

## What I'd Do Differently
_Would you stage this change differently to avoid the lockout scenario? Is there a way you'd sequence future re-IP work to reduce the chance of losing access mid-change?_

## Skills This Demonstrates
_e.g. network segmentation design, NAT/routing fundamentals, safe re-addressing of production-adjacent infrastructure, diagnosing a downstream symptom back to its root cause._

## Evidence
_Addressing table, console screenshots, firewall log excerpts showing the working state._
