# RAID Controller and Storage Configuration — PERC 6/i

## Overview
_What controller do you have, and what capability does it lack that a more modern controller would have? What does that missing capability rule out for this build?_
PERC 6/i is the current and final RAID controller on this server. This controller lacks modern features such as 4Kn drives, and additionally cannot support drives over 2TB in size. It operates at a slower speed as well. These missing capabilities rule out any drives over 2 TB, which caps the total maximum capacity of the server at 10TB (excluding boot drive).
## What I Configured
- Controller model and firmware: PERC 6/i
- Boot volume: Drive 5, RAID 0, 250GB
- Bulk storage volume: Drive 2 & Drive 4, RAID 1, 2 TB (Combined)
- Battery Backup Unit status: Dead/Failing

## Why I Made This Choice
_Why RAID-0 for a single boot SSD rather than leaving it unconfigured? Why RAID-1 for the bulk storage rather than RAID-0 or nothing? Why did the BBU's condition affect your write policy decision, and why is leaving "Force WB with no battery" unchecked the safer choice rather than the faster one? Why hardware RAID here instead of software RAID or ZFS — what specifically about this controller made that decision for you?_
Hardware level RAID was selected due to its superior performance and reliability, additionally being independent of the ProxMox operating system. This reduces load on other components of the server, and supports a lot  of RAID configurations as opposed to software level RAID. However, this will lead to mild inconviniences when new drives are installed, as a physical console will be required, limitation mentioned in iDRAC. RAID-0 provides the proper configuration for the boot SSD, and allows clean data access and drive management. RAID-1 allows for proper mirroring of old HDDs, to prevent a single node of failure.
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
