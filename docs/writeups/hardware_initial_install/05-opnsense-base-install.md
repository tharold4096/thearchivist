# OPNsense Installation — Sentry Gate (Dell Inspiron 530)

## Overview
_What role does this machine play in the two-site architecture, and why does it exist as a separate box rather than a role folded into the server?_

## What I Configured
- OPNsense version installed: _[...]_
- Boot media type used (and why the others failed): _[...]_
- Initial hostname / timezone / NTP status: _[...]_
- Root credential status: _[...]_

## Why I Made This Choice
_Why OPNsense over pfSense? Why is this machine scoped to firewall duty only, with everything else moved to the server — what would have happened if you'd kept the original plan of running multiple services here? Why did you accept a single point of failure for the server's internet access rather than designing around it?_

## How I Did It
_Document the actual boot media saga — the image formats you tried, what "trying MBR in Rufus" actually did and didn't do, and why the nano image was the one that worked. This is one of the strongest debugging stories in the whole build; don't compress it too much._

## Problems I Ran Into
_The dead-keyboard symptom and how you traced it back to a partition table rather than a hardware fault. What ruled out "OPNsense doesn't support this hardware" specifically, and how fast did you rule it out?_

## What I'd Do Differently
_If you were doing this on a different piece of old hardware next time, what would you check about its firmware before downloading any boot image at all?_

## Skills This Demonstrates
_e.g. legacy BIOS vs UEFI troubleshooting, partition scheme literacy (MBR/GPT), disciplined hypothesis elimination, recognizing a misleading diagnostic test._

## Evidence
_Console screenshots, the boot media comparison table, any config backup file references._
