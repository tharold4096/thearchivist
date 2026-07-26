# Cybersecurity homelab — README

This cybersecurity homelab is built off of a two-site architecture, with active SIEM logging, a functional file server, Juice Shop test VMs, and among other useful cyber tools.

## Machine names

|Machine|Hostname|Shorthand|Username|
|-|-|-|-|
|Gaming PC|`towerofpower`|**Tower**|—|
|Dell Inspiron 530|`thearchivist`|**Arch**|`phalanx`|

## The two-machine, two-site architecture

* **Tower (Gaming PC, 48GB RAM) — lives at the dorm.** The primary VM lab: AD environment, Wazuh **manager** (SIEM), Kali, vulnerable targets. Note the flip from earlier drafts of this doc — Tower is the one on campus, not Arch.
* **Arch (Dell Inspiron 530, 4 cores, 3GB RAM) — lives at home**, on the family network. A lightweight second node: Wazuh agent, Docker stack, off-site backup target for Tower's data, and now a family file server. Reached remotely from the dorm over Tailscale.
* **Oracle Cloud VM (Always Free tier)** — public honeypot. Unchanged, not yet started.

Confirmed working: Tailscale doesn't care which physical site is which — Wazuh's agent-to-manager connection, and all remote access generally, works symmetrically regardless of direction, and campus-network UDP restrictions are the kind of thing Tailscale is specifically built to fall back around.

## Why the dorm plan changed (housing policy)

UNT Housing's handbook explicitly bans personal networking gear in residence halls. Under "Prohibited Items (Unless Provided by Housing)":

> "Wireless routers or personal network switches"

— [UNT Housing Policies, Housing Handbook, "Appliances" section](https://housing.unt.edu/housing-policies/housing_handbook/housing_policies.html)

That killed the original travel router (WISP mode) and managed switch plan entirely — for whichever machine ends up in the dorm. UNT's residence hall internet (Boldyn/MyResNet-5G) also authenticates per-device through a registration portal, which reinforces the rule technically, not just on paper.

**Resolution:** whichever machine is on campus (currently Tower) connects directly to MyResNet-5G like any normal device — no local routing/firewalling, no router or switch hardware. **Tailscale** links the two sites together instead; it's outbound-only and needs no router, so it doesn't trip the policy.

## Tower-specific hardening (now that it's the machine on campus WiFi)

Two things that matter specifically because Tower — not Arch — is the box sitting on a shared campus network:

**VM networking mode — NAT/host-only only, no exceptions.** The AD lab, Kali, and the vulnerable targets (DVWA, Metasploitable, Juice Shop) must stay on NAT or host-only networking in VMware/VirtualBox. That keeps them invisible to the physical dorm network — MyResNet only ever sees Tower itself as one device. Switching any VM to **bridged** mode would give it its own IP/MAC on the real network, which is both a genuine exposure risk (a live vulnerable VM reachable by other students) and functionally close to the "personal router" behavior the housing policy targets.

**Windows LLMNR/NBT-NS hardening.** Windows hosts broadcast SMB/LLMNR/NetBIOS/network-discovery/UPnP by default, which is exactly what credential-harvesting tools like Responder are built to exploit on a shared network. Fix: set Tower's network profile to **Public** (not Private/Home) while on MyResNet, and disable LLMNR and NBT-NS via registry or Local Group Policy. Five minutes of work, and a legitimate, resume-relevant line ("hardened a Windows host against LLMNR/NBT-NS poisoning while operating on a shared network").

**Physical, not technical, but worth a line:** a gaming tower in a dorm room means real power draw, fan noise, and a theft target in a room that isn't always locked. A cheap cable lock and being mindful of when loud VM workloads are running are the only practical asks here.

## Hardware — Dell Inspiron 530 / Arch (confirmed specs)

* Chipset: Intel G33 (Northbridge) / ICH9 (Southbridge)
* 4x SATA II ports (300MB/s)
* CPU: 64-bit capable (Inspiron 530 shipped from Celeron 450 up through Core 2 Quad Q9650; even the base Celeron 450 is 64-bit) — confirm the specific chip with `lscpu` once the OS is on
* RAM: 3GB (mismatched DDR2 DIMMs), **not upgrading** — DDR2 kits are 2–3x normal price in the current DRAM shortage, and 3GB is workable for this workload
* Mid-tower form factor (not the slim 530s) — more room to work in than assumed originally
* 1x PCIe x16, 1x PCIe x1, 2x PCI slots (unused, no NIC upgrade needed — Arch was never going to route/firewall anything)

## Storage — split SSD/HDD setup

|Drive|Status|Role|
|-|-|-|
|Used HDD, 500GB–1TB|**Acquired** — CrystalDiskInfo shows a clean/healthy report across the board|Borg backup repository (mirrors Tower's lab configs + Wazuh/SIEM data)|
|SATA SSD, 240GB (Kingston A400 / Crucial BX500 class)|**Pending** — ordered, not yet arrived|OS, Docker, all database-backed containers, swapfile|

Why split: Arch's workload includes several always-on SQLite databases (Vaultwarden, Uptime Kuma) plus Docker's overlay filesystem plus Borg's dedup index — all small, random I/O, which HDDs handle badly and which a 3GB box has zero RAM margin to stall on. Keeping Borg's I/O on a separate physical drive means a backup run can't compete with the containers for disk access while it happens.

**Still to do when the SSD arrives:**

* Mount with a 2.5"→3.5" bracket (\~$5–8, not yet purchased) — the Inspiron's bays are 3.5"
* Physically confirm 2 free SATA data + power connectors before final assembly (should be fine — 4 ports total, only 2 drives so far)
* SATA II caps both drives at 300MB/s regardless of their rated speed — irrelevant for this workload, the latency win from the SSD is what matters, not throughput

## New addition: family file server (Samba, on Arch)

Since Arch lives on the family's home network, it's a natural fit as an off-site-feeling shared drive for the family, and a genuine sandbox for practicing user access control.

**RAM cost — small.** Samba idles around 20–50MB, peaking maybe 100–150MB under active transfers. New estimated total for Arch: \~1.1–1.4GB, still comfortable headroom on the 3GB box.

**Wear and tear — a real behavior change, not just a RAM line.** Right now the acquired HDD's only job is Borg — scheduled, mostly sequential, gentle. A family file share flips that to random, unscheduled access (someone uploads photos at 9pm, someone grabs a document at noon), meaning more head movement and more power-on hours than the drive was tested for. Not abuse, but worth running `smartctl -a` on it every month or two once live, watching reallocated sector count and power-on hours trend rather than assuming today's clean report holds forever.

**Key risk — don't co-locate the family share with the only backup copy.** That HDD is currently Tower's *backup destination*. Making it the family's *only* copy of their files at the same time creates a single point of failure worse than either role alone — one drive failure costs both Tower's off-site backup and the family's only copy, simultaneously. Two fixes, still an open decision:

* **Cheaper:** keep one drive, but add a reverse sync/second Borg repo job that copies the family share back to Tower over the same Tailscale link — gives the family data a real second copy.
* **Cleaner:** buy a second cheap used HDD (\~$15–30, same sourcing as before) and split roles — one drive for Borg, one for the family share, so a single drive failure never costs two things at once.

**Access model:**

* **Family reaches the share locally** — Arch and the family devices are on the same home LAN, so Samba just shows up as a normal network drive at Arch's local IP. No Tailscale, no VPN needed for them.
* **Tailscale stays reserved for remote admin access** — your own access from the dorm, not the family's front door.
* **SSH keys stay for your own administrative login only** — not handed out to family. SSH authenticates a Linux login, not a friendly file share, and it skips right past the per-folder/per-user permission model that's the actual point of the access-control practice. Samba's own user/share/folder permissions are the mechanism to practice with here.

## Software stack by machine

**Tower (Gaming PC, dorm) — VM lab**

* VMware Workstation Pro (free for personal use) or VirtualBox — **NAT/host-only networking only** for every VM, no bridged mode
* Windows Server evaluation ISO (free, 180-day) + Windows 10/11 eval clients — AD environment
* Sysmon + Windows Event Forwarding — host-level logging
* **Wazuh manager** — central SIEM, receives logs from both the local lab and Arch
* Kali Linux — attacker box, used both locally and across the VPN against Arch
* Metasploitable2/3, DVWA, Juice Shop — local vulnerable targets
* Network profile set to **Public**, LLMNR/NBT-NS disabled, while on MyResNet

**Arch (Dell Inspiron 530, home) — second node**

* Ubuntu Server (headless)
* Docker + Docker Compose
* Tailscale (or Headscale) — links back to Tower/dorm; also how you (not the family) reach Arch remotely
* Pi-hole — DNS filtering
* Vaultwarden — self-hosted password manager
* Uptime Kuma — status/alerting dashboard, watches both sites
* Wazuh **agent** (not manager) — ships logs to Tower's Wazuh manager over Tailscale
* Juice Shop — remote attack target, attacked from Kali on Tower across the real VPN link
* **Samba** — family file server, per-user shares/permissions, reached locally over the home LAN
* fail2ban + hardened, key-only SSH (YubiKey-backed once purchased) — your own admin access only, bastion-host hardening practice
* Borg — nightly backup job targeting the dedicated HDD
* 2–4GB swapfile (on the SSD, once installed) — no headroom on 3GB, so this is a safety net, not optional

**Oracle Cloud VM — honeypot (unchanged, not started)**

* Cowrie or T-Pot
* Let it run 2–4 weeks once stood up, then analyze attacker IPs/techniques/timing

## Estimated RAM budget (Arch, all services running including Samba)

|Component|Idle RAM|
|-|-|
|Ubuntu Server base|\~250–300MB|
|Docker daemon|\~100–150MB|
|Wazuh agent|\~80–120MB|
|Pi-hole|\~50–80MB|
|Vaultwarden|\~15–30MB|
|Uptime Kuma|\~120–180MB|
|fail2ban|\~10–20MB|
|Juice Shop|\~200–300MB|
|Samba (idle / active)|\~20–50MB idle, up to \~100–150MB peak|
|Borg (idle; spikes higher during a run)|\~10–20MB|
|**Total**|**\~1.1–1.4GB**, still \~1.4–1.7GB headroom on the 3GB box|

Two known deviations from a flat estimate: swapping in DVWA instead of Juice Shop adds \~250–400MB for its database (use Juice Shop, not DVWA, for this reason); Borg's dedup index spikes during backup runs rather than sitting flat, which is the actual reason swap is mandatory here.

## Build order (Arch)

1. Pi-hole + Vaultwarden + Uptime Kuma first (\~260MB combined) — validates the box is stable before adding load
2. Add the swapfile before anything else goes on
3. Wazuh agent — confirm it's actually shipping logs to Tower's manager over Tailscale before adding more
4. Juice Shop as the attack target, once the SIEM pipeline is proven working
5. Samba file server — set up per-user shares, decide backup-drive co-location vs. second HDD before loading it with real family data
6. Borg backups last, scheduled overnight, deliberately not overlapping with any Juice Shop attack testing

## Budget (current, updated)

|Item|Status|Est. cost|
|-|-|-|
|Used HDD (backup drive)|**Acquired**|\~$15–30|
|SATA SSD, 240GB (OS/Docker drive)|**Pending**|\~$50–65|
|2.5"→3.5" mounting bracket|Not yet purchased|\~$5–8|
|Second used HDD (splits family share from backups)|Open decision|\~$15–30|
|YubiKey Security Key|Open decision|\~$30|
|Small UPS (protects an unattended box)|Open decision|\~$50–70|
|Domain name (1yr, optional — GitHub Pages is free)|Open decision|\~$12|
|**Core total (HDD + SSD + bracket)**||**\~$70–105**|
|**With stretch items**||**\~$147–217**|

Dropped from the original budget entirely — not needed under the current architecture:

* Second NIC (\~$20–30) — neither machine routes/firewalls anything
* Managed switch (\~$35–45) — explicitly banned under UNT housing policy
* Travel router w/ WISP mode (\~$70–100) — explicitly banned under UNT housing policy
* Separate "spare drive for backups" line — superseded by the dedicated Borg HDD above

Both the shortage-driven pricing context from the original doc (DRAM/NAND prices up sharply through 2026, Raspberry Pi pricing roughly doubled) and the "skip the Pi, don't upgrade RAM, buy HDD not SSD for cold storage" reasoning still hold and drove the decisions above.

## Portfolio projects (updated for the two-site setup)

1. **Two-site detection pipeline** — Wazuh manager on Tower (dorm), agent on Arch (home), shipping over an encrypted mesh VPN. Stronger than a single-box setup because it's genuinely two locations.
2. **Remote red-to-blue exercise** — Kerberoasting/exploitation run from Kali (Tower) against Juice Shop (Arch) across the real Tailscale link, caught and logged by Wazuh. More honest than everything living on one machine.
3. **Off-site backup pipeline** — Borg backups of Tower's lab configs and SIEM data, landing on genuinely separate hardware in a different physical location.
4. **Home AD/VM lab writeup** — the original segmentation/AD-attack-chain project, still lives entirely on Tower.
5. **Public honeypot analysis** — Oracle Cloud VM, Cowrie/T-Pot. Unchanged, not yet started.
6. **MFA/passkey + SSH hardening** — YubiKey across a few services, plus key-only SSH on Arch for your own admin access.
7. **Shared-network hardening** — Tower's LLMNR/NBT-NS lockdown and Public network profile while operating on MyResNet. New addition, directly tied to the site flip.
8. **Family access-control sandbox** — Samba per-user shares/permissions on Arch, doubling as a practical, low-stakes place to practice access control before applying the same thinking to the lab itself.
9. **(Optional) automation script** — auto-block an IP after N failed SSH attempts. Natural fit for Arch, since it's the one machine reachable from outside the home network (via Tailscale).

## Open items

* SSD hasn't arrived yet — install with the bracket once it does
* Confirm the Inspiron's CPU is 64-bit via `lscpu` after OS install (expected fine, not yet verified)
* Physically confirm 2 free SATA data + power connectors before final assembly
* Decide: reverse-sync job vs. second HDD, before putting real family data on the Samba share
* YubiKey and UPS purchases are still undecided
* Not currently pursuing a UNT housing exception for a personal router — Tailscale-only is the settled approach, but `housinginfo@unt.edu` is the contact if that's ever revisited

