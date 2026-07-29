# \[Initial Hardware Installation]

**Date:** 2026-07-21
**Machine:** Arch

**Status:** In Progress
**Tags:** Hardware, Drives, OS

\---

## Why I built this

* The purpose of this Homelab initial setup was to cover my current weakness in the realm of networking, access management, and SIEM log evaluation and recording. 
* This initial plan was to setup a simple DNS server off of an old pc, with the added capabilities to potentially serve as an ad-blocker and firewall for my home. 
* Installation of a file server and security tools later on would have helped me manage multiple users, detect unauthorized access attempts, and resolve security related issues in real-time.

## How I built it


* **Tools/stack: Ubuntu server, pi-hole**
* **Key steps:**

  * Reapply thermal paste and diagnose basic hardware failure points
  * Burn Ubuntu server onto USB
  * Install Ubuntu on SSD and verify functionality
  * Locate hardware issues early on, verifying functionality of hard drive with short SMART test
  * Begin installation basic configuration of Swapfile, Pi-hole, Vaultwarden and Uptime Kuma
* **Config/scripts:**

## What broke

* **Symptom:** Pi-hole installation hanging, process dropping and firing back up, killing the process becoming increasingly difficult.
**Initial diagnosis:** Write speed of HDD incompatible with current software, misleading RAM values, faulty form factor of Pi-hole installer.
**Root cause:** Faulty HDD drive, 90% corrupted, unusable for current setup. Failed short SMART test.
**Fix:** Replace HDD with verified used HDD for logging large file writes over night, switch to using SSD for OS and application installations.

## What worked

* Switching to SSD for OS and application installs increased access time, reliability, and backup architecture with used HDD
* Future proofing the system by making used HDD backup only, relying on SSD for day to day operations. More resistant architecture to drive failure.

## What I'd do differently

* Resolve hard drive issues early. Initial install of Ubuntu server was hanging as well the initial attempt, which should have flagged the drive (est. 18y life, with repeated spin ups and downs). The best way to circumvent these issues later down the line are to very the stability with the Tower before install on the Arch. Consider using tools such as Crystal or the native SMART support to check beforehand. Will be performing this verification when new storage parts arrive.

\---

## Resume-ready summary

*One or two condensed, quantified, action-verb-led bullets distilled from everything above. This is the part you'll actually copy into a resume or portfolio site.*

* Troubleshooted server hardware setup issues for two-site architecture homelab.
* Accurately identified failing hard drive early in installation process, before attempting large config setups.
* Tested flow of home lab setup for future attempts, verifying basic hardware checks and upgrade installs.

