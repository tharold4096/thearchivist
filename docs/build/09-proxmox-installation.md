# Proxmox VE Installation — The Archivist

## Overview
_What does this machine become once Proxmox is running, and how does its role differ from what was originally planned for this hardware before the server acquisition changed the architecture?_

## What I Configured
- Proxmox version installed: _[...]_
- Boot media / install method actually used: _[...]_
- Filesystem chosen for the boot volume: _[...]_
- Management IP (initial and post-migration): _[...]_
- Subscription status (enterprise vs no-subscription repo): _[...]_

## Why I Made This Choice
_Why ext4/XFS over ZFS on this specific controller — what does the PERC's lack of passthrough actually force here, and why would ZFS on top of hardware RAID have been the wrong call even if it were possible? Why did you attempt USB, then optical, and evaluate PXE — what made you choose the path you actually used?_

## How I Did It
_Document the actual install path that worked, including how you diagnosed the failures that came before it. If the boot log showed something specific (driver loading, DHCP handshake, media read errors), reference what you learned from reading it rather than just stating the end result._

## Problems I Ran Into
_Walk through the install-media troubleshooting chronologically — what each failed attempt taught you before you landed on the one that worked. Was the RAM reseating a red herring or a real contributor? How did you rule that in or out?_

## What I'd Do Differently
_Knowing the R710's specific quirks now, what install method would you reach for first on the next piece of hardware this age? Would you validate the RAM before or after attempting a boot from unfamiliar media next time?_

## Skills This Demonstrates
_e.g. hypervisor installation and storage-backend tradeoffs, systematic elimination across multiple boot-media types, reading kernel boot logs to diagnose install failures, adapting install strategy to hardware constraints rather than fighting them._

## Evidence
_Installer screenshots, the boot log that revealed the actual failure mode, the working Proxmox dashboard post-install._
