# RAID Controller and Storage Configuration — PERC 6/i

## Overview
_What controller do you have, and what capability does it lack that a more modern controller would have? What does that missing capability rule out for this build?_

## What I Configured
- Controller model and firmware: _[...]_
- Boot volume: drive(s), RAID level, size
- Bulk storage volume: drive(s), RAID level, size
- Write policy chosen: _[...]_
- Battery Backup Unit status: _[...]_

## Why I Made This Choice
_Why RAID-0 for a single boot SSD rather than leaving it unconfigured? Why RAID-1 for the bulk storage rather than RAID-0 or nothing? Why did the BBU's condition affect your write policy decision, and why is leaving "Force WB with no battery" unchecked the safer choice rather than the faster one? Why hardware RAID here instead of software RAID or ZFS — what specifically about this controller made that decision for you?_

## How I Did It
_Walk through the actual VD creation process — how you identified the controller model, how you cleared the drive that was showing as failed, and the steps to build each virtual disk._

## Problems I Ran Into
_The "drive zero failure" investigation is worth documenting fully — what did the error actually mean, how did you distinguish a real hardware fault from stale controller state, and what fixed it? Also worth covering here: the keyboard navigation issue inside the F2 operations menu, and how you worked around it._

## What I'd Do Differently
_Would you replace the BBU rather than accepting write-through? Would you check the controller model before acquiring the server rather than after? Anything about the drive validation process you'd do earlier?_

## Skills This Demonstrates
_e.g. enterprise RAID configuration, distinguishing hardware faults from stale controller metadata, write-cache/data-integrity tradeoff reasoning, working within a controller's real constraints rather than fighting them._

## Evidence
_Screenshots of the VD Mgmt screen, PD status, any SEL entries worth preserving as before/after._
