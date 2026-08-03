# iDRAC6 Configuration and Firmware Update

## Overview

*What is iDRAC, what does it do independent of the host OS, and what tier do you have (Express vs Enterprise) — what does that tier actually mean for how you can manage this server?*
iDRAC is the built in Dell remote management tool (hardware and software), accessible even when the device is powered off. It runs on auxilary power, and supports an external touchpad to configure basic settings and read warnings. The system came installed with Express, which is enough for day to day use. This tier allows the user to power on, off, and reboot the server, monitor temperature and power consumption, and other basic hardware level monitoring. With the Enterprise card lacking, I will not be able to use KVE or have a remote management interface of that kind, but for day to day tasks Express will be enough.
## What I Configured

* Target iDRAC firmware version: 2.92 (Build 05)
* NIC sharing mode selected: Yes
* Static IP assigned: 192.168.10.245
* Root credential status: Updated

## Why I Made This Choice

iDRAC is essential for actions such as remote power on and hardware monitoring. For a server that will be left mostly unattended, remote monitoring is an essential. The update was needed to ensure basic functionality, and that later attempts to monitor systems using this tool did not fail. iDRAC needs its own ip address, because as afformentioned it runs independently of the rest of the hardware. MIC-sharing is also an important setting to note, as with Express license there is no specific management port. Additionally, the importance of changing the default credentials cannot be overstated. With the default credentials, any threats that pass the firewall are able to power on, power off, or change hardware level settings, which could even lead to malicious file uploads through the update interface. 

## How I Did It

The file for all firmware updates must be obtained from the official Dell support website. The process to update iDRAC is different than BIOS, because unlike BIOS, iDRAC is its own controller on its own network stack. This means that there is not a well documented and safe way to update from a USB. The recommended method (as found online) was to simply use the graphical interface. Here you are able to upload a .d6 file, choose the correct options, and update the system. Important: the .d6 file is the correct file format for this update zone, so extracting the .exe file is necessary before attempting to upload it. One alternative method suggested was racadm for these types of updates, but the iDRAC controller was too outdated to handle that format. For hypothetical future updates, racadm is a potential avenue if GUI is down.

## Problems I Ran Into

### TLS
One of the main issues was that web browsers were failing to access the iDRAC GUI. After some troubleshooting and investigation, it was noted that the root cause of this was due to outdated TLS. Modern browsers were refusing the connection on TLS 1.0/1.1, which cause the connection to drop. After attempting racadm (see below), the next option was to use firefox to lower TLS to 1. This successfully allowed connection with iDRAC, which then allowed a successful file upload and firmware update.
### racadm
Racadm caused interesting errors, source unknown. The initial test of racadm caused a hang, so the process was left running for as long as possible. However, after 30 minutes there was no sight of conclusion, so the process was killed. Subsequent attempts to run the command failed to pull the location of the command, so the package was reinstalled. Once a sucessful connection was established with the server, the message returned that racadm was not supported. Noted as most liekly fix was the update, so pivoted to GUI troubleshooting.

## What I'd Do Differently

*Would you set up racadm access differently from the start? Is there a faster way you'd get to a working management path next time, knowing what iDRAC6's limitations are?*
I would first verify racadm before attempting to push any files. The errors in the flags, filepaths, and data types caused me to stay on racadm troubleshooting only to find a dead end. Fix: now that GUI is reliable and updated, I will use GUI for all future updates, and retire racadm for low level troubleshooting if needed.
## Skills This Demonstrates

Out-of-band management on legacy hardware, deprecated TLS, CLI-based remote administration, methodical debugging of silent failure,
## Evidence

9001;CmdNotFound;getsysinfo←\'getsysinfo' is not recognized as an internal or external command,
operable program or batch file.
C:\Windows\System32>"C:\Program Files\Dell\SysMgt\rac5\racadm.exe" -r 192.168.1.245 -i getsysinfo
ERROR: Unable to connect to RAC at specified IP address.
C:\Windows\System32>"C:\Program Files\Dell\SysMgt\rac5\racadm.exe" -r 192.168.1.245 -i getsysinfo
ERROR: Unable to connect to RAC at specified IP address.
C:\Windows\System32>
