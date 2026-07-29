# Booting a Modern BSD Firewall on 2008 Hardware

Installing OPNsense 26.7 on a Dell Inspiron 530 took several failed attempts across two USB drives, three image formats, and one misleading diagnostic. The root cause turned out to be a partition table, and the most visible symptom — a dead keyboard — had nothing directly to do with the keyboard.

This is written up in full because the diagnostic path is more useful than the fix.

---

## The hardware

| Component | Detail | Why it matters |
|---|---|---|
| Board | Intel G33 / ICH9 chipset (2008) | Predates USB 3.0 entirely |
| Firmware | **Legacy BIOS only, no UEFI** | The core constraint |
| RAM | 3GB DDR2 | Adequate for firewall-only duty |
| Storage | 4x SATA II | Known-good, used to boot Ubuntu successfully |

---

## The symptom

Powering on with the OPNsense USB inserted produced a freeze at the Dell splash screen. The F2 and F12 prompts were displayed, but **no keyboard input registered at all** — no BIOS setup, no boot menu.

Removing the drive restored normal behavior. A second, different USB drive carrying the same image produced identical results.

---

## Hypotheses, in the order they were tested

**1. The drive is counterfeit.**

One of the two drives reported an implausibly large capacity for its apparent age. Fake flash drives lie about capacity at the controller level and silently corrupt data past their real physical limit, so this was checked first with a full write-and-verify pass (H2testw).

*Result: genuine.* Ruled out — but the test was worth running, and the same drive was later rejected for an unrelated reason.

**2. USB 3.0 on a pre-USB-3.0 chipset.**

The larger drive had a red connector, indicating SuperSpeed. A 2008 BIOS's USB stack was never written against USB 3.0 controllers, and enumeration hangs are a documented consequence.

*Result: contributing but not sufficient.* This is a real problem on this board — that drive is unsuitable as boot media here regardless. But the second drive was USB 2.0 and failed identically, so it wasn't the whole story.

**3. Partition scheme mismatch (MBR vs GPT).**

Legacy BIOS expects MBR. The imaging tool was set to MBR and the drive rewritten.

*Result: no change — but this test was invalid.* When a raw `.img` is written, the tool performs a byte-for-byte copy and the partition table comes from **inside the image file**. The MBR/GPT selector applies only to the tool's formatted modes and is ignored during a direct image write. The drive still received whatever the image contained.

This false negative pushed the investigation away from the correct answer for a while.

**4. OPNsense doesn't support this hardware.**

*Ruled out immediately by timing.* The freeze occurs at the Dell splash — during POST, before control passes to any bootloader. No OPNsense or FreeBSD code has executed at that point. Whatever fails, it fails while the BIOS is reading the drive, not while an operating system is running on it.

**5. Something about the USB subsystem generally.**

An Ubuntu Server installer USB was booted on the same machine, same port.

*Result: worked perfectly, keyboard fully responsive.* This cleanly eliminated the USB ports, the controller, legacy USB support, and the attached SATA drive as causes. It also reframed the question: the problem isn't USB, it's **what's on the drive.**

---

## Root cause

Ubuntu ships an *isohybrid* image — deliberately built with a conservative MBR structure so it boots on essentially any firmware, including hardware from this era. OPNsense's `vga` and `serial` images are raw FreeBSD disk images using **GPT** with `freebsd-boot` and `freebsd-ufs` partitions.

A GPT layout on a legacy-BIOS-only board from 2008 is exactly the kind of thing that firmware's partition-parsing routine was never written to handle.

**And the keyboard symptom follows directly from this.** On ICH9-era boards, legacy USB keyboard support is emulated by the BIOS's own USB stack via SMI traps. When that stack hangs partway through device enumeration, HID emulation dies along with it. The dead keyboard was never a separate fault — it was the visible edge of the BIOS being stuck.

---

## Image format comparison

OPNsense publishes several image types. They are not interchangeable, and the differences are load-bearing on old hardware.

| Image | Format | Partition scheme | Result on this board |
|---|---|---|---|
| `vga` | Raw `.img` | **GPT** | Hangs at POST, kills USB keyboard |
| `dvd` | ISO 9660 / El Torito | Optical | **Not USB-bootable** — no boot marker; both Rufus and Etcher correctly reject it |
| `nano` | Raw `.img` | **MBR** | **Works** |

Two things worth knowing about the `dvd` image: it is intended for optical media, and the "not bootable" warnings from imaging tools are accurate rather than spurious. It was a dead end for USB installation, though burning it to an actual disc remained a viable fallback since the machine has an optical drive.

The `nano` image turned out to be the right answer for reasons beyond partition scheme:

- It is **preinstalled**, not an installer — write it and boot into a working system with no install step
- It is **designed for flash media** with reduced write activity, which addresses USB wear by design rather than by configuration
- Despite documentation implying serial console orientation, **it output to VGA without any special handling** on this hardware

---

## Post-install hardening for USB boot media

Flash media has finite write endurance, and a firewall writes continuously — state tables, DHCP leases, firewall logs, and eventually IDS alerts.

- **RAM disks for `/tmp` and `/var`** redirect the frequent small writes to memory. Verify with `mount | grep -E '/tmp|/var'` and look for `md` devices. The nano image is built with this in mind.
- **Tradeoff:** logs do not survive a reboot. Acceptable for a firewall; worth revisiting when an IDS starts generating real volume.
- **Config backups matter more than usual.** The boot media is a consumable. An exported `config.xml` turns a dead USB stick into a ten-minute rebuild instead of an evening.

---

## What generalizes

**When the failure happens tells you more than what fails.** A hang before any OS code runs eliminates an entire category of hypothesis in one observation.

**Verify that a test tests what you think.** "I tried MBR" was a reasonable-sounding test that changed nothing about the drive. The Ubuntu boot was the good test precisely because it isolated one variable cleanly and produced an unambiguous result.

**Symptoms can be several layers away from causes.** A dead keyboard was a partition table problem. Earlier in the same project, installer hangs on a different machine turned out to be a failing hard drive. When behavior seems impossible, question the layer below the one being examined.

**Read the tools' warnings as data.** Two independent imaging tools rejecting the same file was information, not an obstacle to route around.

---

## If this hardware had refused entirely

Worth recording, since it was researched during the process: if FreeBSD-based boot media had proven fundamentally incompatible, **pfSense would not have been an escape hatch** — same FreeBSD base, same image structure, same likely outcome.

Linux-based alternatives would boot like the Ubuntu image did:

| Option | Notes |
|---|---|
| **IPFire** | Closest equivalent in role — web UI, security-focused, runs comfortably in 2GB |
| **VyOS** | CLI-driven, enterprise-credible configuration syntax, steeper learning curve |
| **OpenWrt x86** | Lightweight and well-established, more router-oriented than firewall-oriented |
| **Debian + nftables + Suricata** | Guaranteed to boot, most educational, no GUI |
