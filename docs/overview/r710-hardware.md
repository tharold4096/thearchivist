The Archivist — Dell PowerEdge R710 context file

Created July 29, 2026. Companion to cybersecurity-homelab-project-plan.md. Server is CONFIRMED ACQUIRED. This file resolves the "PROPOSED, NOT CONFIRMED" caveat and the "unknowns pending hardware" section of the main plan, and adds constraints that were not visible before the model was known.

1. Confirmed baseline
Component	State	Notes
Model	Dell PowerEdge R710, 2U rack	Gen 11 PowerEdge, launched 2009, Intel 5520 chipset
CPUs	Both sockets populated	SKU unknown — must verify. LGA1366, Xeon 5500 (Nehalem) or 5600 (Westmere)
RAM	All 18 slots × 16GB = 288GB expected	DDR3 Registered ECC. Verify total at POST
PSUs	Two, redundant	570W Energy Smart or 870W High Output — verify label
Drives	NONE	Blocking. No caddies either.
SD cards / IDSDM	NONE	Removes the "boot from mirrored SD" option
Onboard NICs	4 × Broadcom NetXtreme II BCM5709 1GbE	Not previously accounted for — this is a win
RAID controller	Unknown	PERC 6/i, H200, H700, or SAS 6/iR. Determines the entire storage design.
Chassis variant	Unknown	6 × 3.5" LFF or 8 × 2.5" SFF. Determines which caddies to buy.
iDRAC	Unknown (Express vs Enterprise)	Enterprise = dedicated NIC + virtual console. Express = shared NIC, no console.
Physical dimensions — verify against the closet before anything else
Height 3.4" (2U) · Width 17.44" · Depth 26.8"
Weight up to 57 lb in max config; with 18 DIMMs and 2 PSUs, assume 45–55 lb
Add 4–6" behind it for power cords and ethernet without sharp bends
Realistic front-to-back requirement: ~32–33"
2. Hard constraints (cannot be designed around)
Legacy BIOS is the safe boot path. UEFI exists on late R710 BIOS but is inconsistent; Proxmox ZFS-on-root is documented as BIOS-mode-only on this generation. Same lesson as the OPNsense nano/MBR saga — do not fight the 2009 firmware.
Cannot boot from NVMe. No option ROM for it. NVMe on a PCIe adapter can be storage but not boot without a chainloader hack (Clover/rEFInd on an SD/USB).
PCIe 2.0 only, no bifurcation. 4 slots (2× x8, 2× x4) plus one dedicated storage slot.
Drives require Dell hot-swap trays. Bare drives do not mount. Not optional.
iDRAC is the fan controller. If iDRAC is dead, misconfigured, or mid-firmware-update, fans run at 100% and there is no OS-level override.
Memory tops out at 288GB, but 3 DIMMs per channel forces the clock down to 800MT/s. Fully populating costs bandwidth.
Out of Dell support. Firmware still downloadable, but no new fixes. iDRAC6 is frozen at 2.92.
3. Flags
TIER 1 — could invalidate the closet plan

F1 — Physical fit. Measure the closet today. ~32–33" of front-to-back clearance and a shelf rated for 60 lb. Most bedroom/hall closets are 22–26" deep. If it does not fit, the closet plan is dead regardless of how well everything else goes — this is now the top blocking item, ahead of the second NIC. It cannot be stood on end: airflow is strictly front-to-back and the drive backplane is not designed for it. No rails means a shelf or the floor; a wire shelf is questionable at this weight.

F2 — Noise. Loud at stock; manageable but not free. Five 92mm Nidec BetaV fans plus PSU fans. Stock behavior is loud enough that people report being unable to hold a conversation next to one. Mitigation is well documented and works on iDRAC6:

# disable automatic control
ipmitool raw 0x30 0x30 0x01 0x00
# set static speed (last byte = % in hex; 0x14 = 20%)
ipmitool raw 0x30 0x30 0x02 0xff 0x14
# restore automatic control
ipmitool raw 0x30 0x30 0x01 0x01

Caveats that matter:

Manual fan mode is transient. It does not survive a reboot, an iDRAC reset, or a cold power-cycle. It needs a daemon or cron job with a temperature safety threshold that re-enables automatic control (see the R710-Fan-Control repos in §6).
PSU fans are not controllable by these commands. There is a noise floor you cannot get under.
Adding a third-party PCIe card (a NIC, an HBA) triggers a blind fan ramp on this generation. Documented on R710 with PERC 6/E specifically.
A closed closet door with a ~200W heat source and no airflow raises inlet temperature, which raises the fan curve. Reducing fan speed and enclosing the box push in opposite directions. Plan for a vented door, a louvered panel, or a gap.

F3 — Power draw. Talk to your parents with real numbers. Dell's own SPECpower results for R710 (X5675, X5670, X5570) land at 62–65W active idle and 172–232W at full load — but those test configs ran minimal RAM and a single drive. 18 × 16GB RDIMMs adds roughly 55–90W by itself. Realistic expectation:

Idle: 150–200W
Loaded: 280–350W

At 175W continuous and ~$0.14/kWh: ~1,530 kWh/year, roughly $215/year. This is a real number to put in front of whoever pays the bill, before the server is plugged in, not after. Buy a Kill-A-Watt and measure rather than argue from estimates.

Mitigation worth taking seriously: depopulate the RAM. You will not use 288GB. Twelve sticks (2 DIMMs per channel) gives 192GB at 1066MT/s; six sticks gives 96GB at 1333MT/s. Both are quieter, cooler, cheaper to run, and faster per-DIMM than 288GB at 800MT/s. Keep the pulled sticks as cold spares. "I right-sized the hardware to the workload" is a better portfolio line than "I maxed it out."

TIER 2 — blocks build progress

F4 — Caddies are mandatory, and the part number depends on the chassis variant. Determine 3.5" vs 2.5" chassis first, then order.

3.5" LFF trays: F238F (also sold as 0F238F, X968D, 0X968D, G302D, KG1CH)
2.5"→3.5" hybrid adapter to put the SSD in an LFF bay: 9W8C4 — or buy an F238F that ships with the adapter bracket
2.5" SFF trays (if that chassis): G176J / 0G176J / 8FKXC
Cost: ~$8–15 each from third parties (WorkDone, HighFine, generic eBay), ~$25–40 for genuine Dell
The borrowed SSD mount from work almost certainly will not fit. That question from the main plan is now answered: you need a Dell tray, not a generic bracket.

F5 — The RAID controller likely cannot do passthrough, which changes the storage design.

Controller	Speed	>2TB drives	True HBA / JBOD passthrough
PERC 6/i	3Gb/s	No — 2TB cap	No
SAS 6/iR	3Gb/s	No	Nominally yes; flashable to IT mode
PERC H700	6Gb/s	Yes (current FW)	No
PERC H200	6Gb/s	Yes	Yes, when crossflashed to LSI IT mode

Consequences:

If it's a PERC 6/i or H700, ZFS is off the table as designed. The usual workaround — exposing each disk as a single-drive RAID0 — is not passthrough; it hides or mangles SMART data. That collides directly with your own stated principle that drive health is foundational. Do not accept a setup where you cannot read SMART.
If it's a 6/i or H700, hardware RAID1 is actually the correct call, not a compromise. Build the mirror in the controller BIOS, put LVM on top, and monitor drive health through the controller (perccli / megacli / smartctl -d megaraid,N).
If you want ZFS, budget for an H200 flashed to IT mode or an LSI 9211-8i (~$20–40 used). Note the internal cabling differs between controller generations — PERC 6/i uses SFF-8484, H200/H700 use SFF-8087 — so a controller swap may need a new backplane cable.
A PERC 6/i also caps your 240GB SSD at 3Gb/s (~270MB/s) and blocks TRIM. Not fatal for a boot drive, but worth knowing.

F6 — Boot media, with no drives and no SD cards. Options in order of preference:

240GB SSD in a caddy on the controller — cleanest. What the main plan already assumed. Requires a caddy + hybrid adapter.
SSD on an internal SATA port (the one feeding the optical drive, plus a second header). Keeps the boot device off the RAID controller entirely, which sidesteps F5 for the boot disk. Needs a SATA power feed and a place to zip-tie the drive; set SATA operation to AHCI, not "RAID On". Reported working, but it is a cable-management hack.
Internal USB port — physically easiest, and Proxmox will chew through the stick. Only viable if / lives elsewhere and the USB holds only /boot via proxmox-boot-tool. Not recommended as a first build.

Whatever you choose: install in Legacy BIOS mode.

TIER 3 — operational and security

F7 — iDRAC6 is a security liability. Treat it as such, and write it up.

Web UI negotiates TLS 1.0/1.1 only — modern browsers refuse it outright. Access needs an old browser build, a TLS-downgrading proxy, or a purpose-built launcher.
Virtual console is Java JNLP with no HTML5 option (HTML5 console arrived on iDRAC7+). Getting it working requires installing Java 7/8 and commenting out jdk.tls.disabledAlgorithms / jdk.jar.disabledAlgorithms in java.security — i.e. deliberately weakening the client.
Firmware ceiling is 2.92. There is nothing newer coming.
Therefore: iDRAC6 goes on the Sentry Gate LAN segment (192.168.10.0/24) and is reachable only via Tailscale. Never on the family LAN, never port-forwarded, never on WAN. This is exactly the segmentation your architecture already provides — the R710 makes it mandatory rather than merely tidy.
Also change the default credentials (root / calvin) immediately. Assume the previous owner did not.
Portfolio angle: "managing an out-of-support out-of-band interface with obsolete TLS, and the compensating controls used to do it safely" is a genuinely good writeup and more interesting than a clean modern build.

F8 — Identify the CPU SKU. AES-NI depends on it.

Xeon 5600 series (Westmere: X56xx, E56xx, L56xx) — has AES-NI. Maps to Proxmox x86-64-v2-AES.
Xeon 5500 series (Nehalem: X55xx, E55xx, L55xx) — no AES-NI.

This matters for WireGuard/Tailscale throughput, LUKS, and Borg. The fact that 16GB DIMMs are installed and 288GB is claimed strongly suggests 5600-series, but confirm:

lscpu | grep "Model name"
lscpu | grep -o aes
grep -o aes /proc/cpuinfo | head -1

If it is a 5500-series, a pair of used L5640s or X5650s is $15–40 and worth it for the AES-NI alone (and the L-series drops TDP to 60W, which helps F2 and F3 simultaneously).

F9 — Memory population is a real trade-off, not a "fill it up" decision. See F3. Decide this before the first boot, because it is a screwdriver job now and a downtime job later.

F10 — Four onboard gigabit NICs change the networking picture. This is genuinely useful and was not in the plan. It means:

No NIC purchase needed for the Archivist
Enough ports to do real VLAN segmentation work between VMs, or to give the Wazuh manager its own interface
A second physical path to Sentry Gate if you ever want out-of-band management separate from data
Broadcom bnx2 is a mature, stable Linux driver — no FreeBSD-style driver roulette here

F11 — Silicon-level vulnerabilities are unpatchable and that's fine, in context. Dell did ship a Spectre/Meltdown microcode BIOS for the R710, with a documented performance cost and a history of stability complaints. Linux can also load microcode at boot (intel-microcode). Nehalem/Westmere will never be fully mitigated against later speculative-execution work.

Framing: this is acceptable for a lab that is never internet-facing and runs no untrusted multi-tenant workload — which describes your architecture. It becomes a genuine finding the moment you consider exposing anything. Note it, mitigate what you can, and be able to explain the reasoning. That's a better answer in an interview than pretending the box is current.

F12 — Non-Dell drives may throw health warnings. Consumer SATA drives (Kingston A400, Crucial BX500, generic 1TB HDD) generally work, but expect "unvalidated" warnings and possibly degraded SMART visibility through a PERC. A minority of people report having to switch drive models entirely.

4. What this changes in the main plan
Main plan item	Status now
"Is the server actually available?"	RESOLVED — confirmed, R710
"Server form factor, noise, power draw"	RESOLVED — 2U, loud, ~150–200W idle. Now Tier 1 flags F1/F2/F3
"The 2.5"→3.5" bracket may be moot"	RESOLVED — need Dell F238F + 9W8C4, not a generic bracket
"RAID controller and whether it flips to HBA"	NARROWED — likely no HBA mode. Identify the exact card, then pick RAID1-in-controller vs buying an H200
"Drive caddy requirements"	RESOLVED — mandatory, part numbers in F4
"Whether the closet needs airflow work"	YES, almost certainly. And it may not fit at all — F1
Second NIC for Sentry Gate	Unchanged, still needed (Archivist's 4 NICs don't help the Inspiron)
UPS "upgraded from optional"	Re-scope. A $50–70 unit at 200W draw buys 2–4 minutes. That is enough for a clean shutdown, which is all you need — but size it deliberately and configure NUT/apcupsd to actually trigger the shutdown, or the UPS is decoration
Tower's post-server role (blocking)	Easier now. With 12+ cores and 96GB+ at home, the Archivist can hold everything except the attacker. "Tower → Kali + AD" or "Tower → Kali only" both become clean
Wazuh manager placement	Archivist. It has the RAM and it's the always-on box
Powerline adapters	Unchanged, buy them now — server is confirmed
New decision this forces

24/7 or on-demand? At ~$215/year and audible from outside a closed door, "power it on when I'm working" is a legitimate answer. But it conflicts with Vaultwarden, Uptime Kuma, the DNS resolver role, Borg backup schedules, and a Wazuh manager that needs to be up to receive agent logs. Pick one:

24/7: accept the cost and noise, depopulate RAM to cut both, invest in closet airflow
On-demand: move the always-on services somewhere else (they were originally scoped for the Inspiron for exactly this reason), and treat the Archivist as a lab that boots when needed. iDRAC remote power-on makes this practical from the dorm.

This should be decided before services get migrated, not after.

5. First-boot checklist

Before power:

Measure the closet. Confirm ~32–33" clearance and a 60 lb shelf. Do this first.
Open the lid. Photograph and record: CPU SKUs (heatsinks off or read the BIOS), RAID controller model, iDRAC card presence, chassis variant (count and size the front bays), PSU wattage label.
Decide RAM population before closing the lid.
Blow it out. A decade-old server from a decommission is full of dust, and dust is why fans ramp.

First boot, on a bench with a monitor and keyboard — not in the closet: 5. Note the POST fan spike; it is normal and one-time. Do not judge the noise until it settles. 6. F2 → BIOS. Record BIOS version. Confirm total RAM and both CPUs detected. Set Boot Mode: BIOS. Set SATA operation to AHCI if you plan to use internal ports. Verify C1E enabled (disabling it forces higher fan RPM). 7. Ctrl+E → iDRAC setup. Set a static IP on the 192.168.10.0/24 plan. Change the root/calvin password. Determine Express vs Enterprise. 8. Ctrl+R → RAID controller BIOS. Record exact model and firmware. 9. Firmware updates: BIOS, iDRAC (→ 2.92), Lifecycle Controller, PERC. Easiest path is booting a live Linux USB and applying Dell's .BIN updates, since the Java console will fight you. Expect a fan ramp during the iDRAC update — do not interrupt it, a bricked iDRAC means permanent 100% fans. 10. Baseline the power draw with a Kill-A-Watt at idle. Write the number down; it's your argument with the electricity bill. 11. Install ipmitool and test the fan commands from §F2 before deciding the closet is viable.

Then, per the main plan: boot media → hypervisor → RAID1 before any real data → service migration.

6. URLs

Dell official documentation

R710 Technical Guidebook (the authoritative reference — memory population rules, rack dimensions, storage options): https://i.dell.com/sites/doccontent/business/solutions/engineering-docs/en/Documents/server-poweredge-r710-tech-guidebook.pdf
R710 spec sheet (quick reference): https://i.dell.com/sites/csdocuments/Shared-Content_data-Sheets_Documents/en/R710-SpecSheet.pdf
R710 Owner's Manual — see the "System Memory" section for exact DIMM population order: https://dl.dell.com/manuals/all-products/esuprt_ser_stor_net/esuprt_poweredge/poweredge-r710_owner's manual_en-us.pdf
Dell side-channel vulnerability advisory (Spectre/Meltdown by model): https://www.dell.com/support/article/us/en/04/sln308587/microprocessor-side-channel-vulnerabilities-cve-2017-5715-cve-2017-5753-cve-2017-5754-impact-on-dell-products
Energy Star datasheet, 570W PSU variant: https://i.dell.com/sites/csdocuments/Shared-Content_data-Sheets_Documents/en/poweredge-r710-570w-energy-star-datasheet.pdf

Power measurements (independent, third-party benchmarked)

SPECpower, R710 with X5675: https://spec.org/power_ssj2008/results/res2011q4/power_ssj2008-20111018-00402-power.html
SPECpower, R710 with X5670: https://ftp.spec.org/power_ssj2008/results/res2010q3/power_ssj2008-20100727-00278-power.html
Read these for the load curve, not the absolute numbers — their configs had far less RAM than yours.

Fan control

R710-Fan-Control daemon (most actively maintained fork, systemd service, temperature-servoed): https://github.com/spacelama/R710-Fan-Control
Original R710-IPMI-TEMP bash script (simpler, cron-driven, easier to read first): https://github.com/NoLooseEnds/Scripts/tree/master/R710-IPMI-TEMP
Step-by-step walkthrough with Proxmox: https://jono-moss.github.io/post/dell-r710-how-to-quiet-the-fans/
Current overview of iDRAC/iLO fan tuning across generations, including what still works on iDRAC6: https://computingforgeeks.com/idrac-ilo-fan-power-tuning/
Third-party-card fan ramp explanation and workarounds: https://techmikeny.com/blogs/techtalk/how-to-lower-fan-speed-after-installing-third-party-card

iDRAC6 access

Remote setup guide including a pre-extracted 2.92 firmimg.d6 for non-Windows updating: https://people.duke.edu/~tkb13/courses/ece566-2025sp/resources/idrac6-remote-setup.pdf
Python launcher for the iDRAC6 virtual console, avoids browser Java entirely: https://github.com/gethvi/iDRAC6VirtualConsoleLauncher
The java.security workaround, if you go the browser route: https://www.violetdragonsnetwork.co.uk/how-to-fix-idrac6-java-8-virtual-console/

Storage controllers

Practical notes on PERC 6/i, H700, H800 limitations and passthrough — read before deciding on ZFS: https://east.fm/posts/dell-server-notes/index.html
TrueNAS forum thread on PERC 6/i vs SAS 6/iR for JBOD: https://www.truenas.com/community/threads/dell-r610-with-perc-6i-versus-sas-6-ir-jbod.27264/
OpenZFS maintainers on why RAID-card JBOD ≠ IT mode: https://github.com/openzfs/zfs/discussions/14458

Caddies

F238F 3.5" tray with 2.5" adapter included: https://www.amazon.com/WorkDone-Drive-Compatible-PowerEdge-Server/dp/B0837SSBYN
F238F reference listing with full cross-compatible part numbers: https://www.harddrivesdirect.com/product_info.php?products_id=463199_F238F&currency=USD

Proxmox

Hardware requirements: https://pve.proxmox.com/wiki/FAQ
CPU type reference — confirms x86-64-v2-AES requires Westmere or newer: https://pve.proxmox.com/pve-docs/chapter-qm.html
R710-specific install thread, including the BIOS-mode-only note for ZFS root: https://forum.proxmox.com/threads/installation-questions-for-proxmox-5-4-on-dell-poweredge-r710.54083/

Physical

R710 rack/dimension reference: https://www.racksolutions.com/news/blog/dell-poweredge-r710-specs-and-rack-compatibility/
7. Portfolio additions this hardware unlocks

Beyond the ten projects already in the main plan:

Thermal and acoustic engineering on enterprise hardware in a residential environment — IPMI fan curve control with a temperature safety threshold, measured dB and inlet temps before and after, and the honest limits (PSU fans, transient manual mode, the enclosure-vs-cooling tension). This is a systems-thinking story, not a security story, and it stands out precisely because most homelab writeups skip it.
Right-sizing legacy hardware — measured power draw across RAM populations, with the reasoning for running 96–192GB instead of 288GB. Cost, thermal, and bandwidth analysis. Demonstrates judgment rather than maximalism.
Securing an out-of-support out-of-band management interface — iDRAC6's TLS 1.0-only web stack and Java console, the compensating controls (network isolation behind Sentry Gate, Tailscale-only reachability, credential rotation), and an honest threat model. Directly relevant to anyone who has inherited legacy infrastructure, which is most real security work.
Storage controller constraint analysis — why the PERC's lack of passthrough dictated hardware RAID1 over ZFS, and how SMART monitoring was preserved anyway. Shows you read the hardware before designing around it.
8. Standing reminders
Nothing you'd hate to redo goes on this box until bulk storage is mirrored. Unchanged from the main plan, and more important now that the controller may hide SMART data.
Do not co-locate the family Samba share with the only Borg repository on the same physical drive. Also unchanged.
Do not interrupt an iDRAC firmware update. A bricked iDRAC means permanent 100% fan speed and no remote management, with board replacement as the only fix.
Bench it before you closet it. Every unknown in §1 is answered faster with a monitor attached and the lid off.
The pattern from the OPNsense build applies here too: when something behaves impossibly on 2009 hardware, question the layer below the one you're looking at. Firmware, partition scheme, and controller mode caused every hard problem in this project so far.
