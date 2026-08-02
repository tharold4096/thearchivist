# iDRAC6 Configuration and Firmware Update

## Overview

*What is iDRAC, what does it do independent of the host OS, and what tier do you have (Express vs Enterprise) — what does that tier actually mean for how you can manage this server?*

## What I Configured

* Starting iDRAC firmware version: *\[...]*
* Target iDRAC firmware version: *\[...]*
* NIC sharing mode selected: *\[...]*
* Static IP assigned: *192.168.1.245*
* Root credential status: *\[...]*

## Why I Made This Choice

*Why does iDRAC need its own IP address separate from the host OS? Why static rather than DHCP? Why does the NIC-sharing decision matter for the eventual network segmentation plan? Why change the default credentials specifically on this interface?*

## How I Did It

*Document the actual firmware update procedure — where you got the file, why the format mattered (the .exe wrapper vs the .d6 payload), and which tool actually worked for you (racadm vs web GUI) and why the other one didn't.*

## Problems I Ran Into

*The TLS/browser issue is worth documenting in detail here — what exactly failed, what ERR* code or message appeared, and what the underlying cause was. Also cover the racadm PATH confusion and the silent-hang debugging process — what did you check, in what order, to figure out nothing was actually running?\_

## What I'd Do Differently

*Would you set up racadm access differently from the start? Is there a faster way you'd get to a working management path next time, knowing what iDRAC6's limitations are?*

## Skills This Demonstrates

*e.g. out-of-band management on legacy hardware, working around deprecated TLS, CLI-based remote administration, methodical debugging of a silent failure.*

## Evidence

*Screenshots of the iDRAC dashboard, firmware version before/after, any command output you want to preserve.*

