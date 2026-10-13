# BIOS Firmware Update — Dell PowerEdge R710

## Overview

*The BIOS for the Dell r710 was outdated, and needed to be update to the 6.6.0 version. This was the last supported version of bios, and had security patches along with quality of life patches. Previous attempts to boot into a live ubuntu server USB had failed, BIOS was flagged as potential issue. Various difficulties in attaining correct image, settled of FreeDOS recommended by online forums experiencing the same issue.*

## What I Configured

* Starting BIOS version: Outdated, \~2.7
* Target BIOS version: *6.6.0*
* Update method used: *FreeDOS executable*
* Boot mode required for the update: Normal, *C:, USB*

## Why I Made This Choice



The purpose of updating the BIOS first was to ensure the install later on passed, the system monitoring and drive detection was working, and there were no security vulnerabilities as I moved on. Version 6.6.0 was chosen because it is the last version that was supported for this hardware by Dell, anything past that would not be compatible with the hardware of the r710. This was essential to perform first to ensure reliability of OS installation through USB, other firmware level updates (iDRAC, PERC 6/i), and system health monitoring.

## How I Did It

The first step was to confirm the BIOS needed this update and identify the drivers that needed to be installed. To do this, navigate to the dell support page and type the service tag ID to locate the specific model of the hardware. Then, filter by BIOS updates and find the most up to date version. Download the file as a .exe, making sure it is the clustered version containing all the files. After extracting, the file should be under payloads folder. To continue, format the USB drive using rufus in FreeDOS formatting structure, and drop the .d6 file into the drive. Plug the drive and boot up into the boot menu, selecting the USB drive as the target. Once FreeDOS loads, execute the payload by typing the name shown (dir). This will perform the BIOS update. Do not power off, disconnect, or reboot the system until the update is complete. NOTE: keyboard hangs are common on older hardware, unplug and plug the keyboard back in if control is lost.

## Problems I Ran Into

*What went wrong along the way? For each issue: what did the symptom actually look like, what was your first hypothesis, and what turned out to be the real cause? (There were several false starts here — Ubuntu Desktop, Ubuntu Server, the Linux DUP package. What did each one teach you before you landed on the method that worked?)*

Attempted to use three different approaches for loading BIOS driver before settling on FreeDOS. The first was a flashed Ubuntu Desktop image using Balena Etcher, failed on install screen. Thought the desktop graphics were the issue, switched to ubuntu server through the same method. When that failed, I attempted to burn the .bin file directly from Dell's website onto the USB, which never appeared on the boot menu. Did research and found threads of similar experiences with PowerEdge series, FreeDOS method recommended, proceeded with update.

## What I'd Do Differently

The first thing I would check in the future is the website to find the most up to date supported driver, and then compare that against what I see in BIOS. I would look for people using similar hardware for advice before attempting to use a recommended method. USB verified first, skipping straight to the least requirement install method.

## Skills This Demonstrates

Legacy firmware update methodology, USB imaging and formatting architecture, filtering of boot drive errors through scope narrowing, reading vendor documentation for EOL hardware.

## Evidence

https://www.reddit.com/r/homelab/comments/bdohuj/unable\_to\_update\_r710\_bios\_or\_other\_drivers\_via/

https://www.dell.com/support/product-details/en-us/servicetag/0-L21Lb0lYbWRMMW1NblluellTMTZXQT090/drivers

