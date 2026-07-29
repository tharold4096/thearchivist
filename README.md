# Two-Site Cybersecurity Homelab

A working security lab split across two physical sites — a university dorm room and a family home — connected by an encrypted mesh VPN. Built on repurposed and second-hand hardware under real constraints: a housing policy that bans network equipment, discontinued residence-hall ethernet, and a shared family network that must not be disrupted.

This repo documents the build, the reasoning behind the architecture, and the troubleshooting that produced it.

---

## Architecture

```
DORM                                  HOME
┌──────────────────┐                  ┌────────────────────────────────┐
│  Tower           │                  │  Home router (family LAN)      │
│  Gaming PC, 48GB │                  │  192.168.1.0/24 — untouched    │
│  AD lab, Kali,   │                  └───────────────┬────────────────┘
│  Wazuh, targets  │                                  │ powerline
└────────┬─────────┘                                  ▼
         │                            ┌────────────────────────────────┐
         │                            │  Sentry Gate (Dell Inspiron    │
         │                            │  530, OPNsense 26.7)           │
         │      Tailscale mesh        │  WAN: 192.168.1.x              │
         └───────────────────────────►│  LAN: 192.168.10.0/24          │
                                      └───────────────┬────────────────┘
                                                      │
                                                      ▼
                                      ┌────────────────────────────────┐
                                      │  The Archivist                 │
                                      │  Enterprise server (planned)   │
                                      └────────────────────────────────┘
```

Family devices connect to the home router directly. They never route through Sentry Gate, never see its subnet, and are unaffected if it fails. This containment is the single most important design constraint in the project.

---

## Hardware

| Host | Hardware | Site | Role |
|---|---|---|---|
| `towerofpower` | Custom PC, 48GB RAM | Dorm | VM lab — AD environment, Kali, vulnerable targets |
| `sentrygate` | Dell Inspiron 530 (2008), Intel G33/ICH9, 3GB DDR2 | Home | Inline OPNsense firewall |
| `thearchivist` | Decommissioned enterprise server | Home | Core lab node — **not yet acquired** |
| — | Oracle Cloud Always Free VM | Cloud | Honeypot — planned |

---

## Current status

| Component | State |
|---|---|
| OPNsense on Sentry Gate | Running — 26.7 amd64, nano image on USB |
| Console + web GUI | Working |
| Tailscale remote access | **Working and verified from outside the home network** |
| Firewall rules | Default-deny with an explicit host allowlist for admin access |
| Second NIC | Not purchased — blocks the WAN/LAN split |
| Suricata IDS/IPS | Not yet installed |
| Enterprise server | Proposed, not confirmed |
| Powerline link | Not purchased |

Sentry Gate currently runs on a single interface as a staging environment. It is not yet inline; that is gated on the second NIC.

---

## Repo contents

| Document | What's in it |
|---|---|
| [`docs/build-log.md`](docs/build-log.md) | Chronological record of the work, session by session |
| [`docs/opnsense-legacy-bios-boot.md`](docs/opnsense-legacy-bios-boot.md) | Getting a modern BSD firewall to boot on 2008 hardware — the longest and most instructive troubleshooting sequence in the project |
| [`docs/remote-access-tailscale.md`](docs/remote-access-tailscale.md) | Mesh VPN access to the firewall, and debugging why a correct-looking rule silently dropped traffic |
| [`docs/network-architecture.md`](docs/network-architecture.md) | Design decisions, addressing plan, DNS hardening, and what was deliberately left out |

---

## Design principles

These emerged during the build rather than being decided up front, and they drove most of the architecture:

**Blast radius over capability.** Every design choice was evaluated on what breaks when it fails. The firewall sits on one machine's network leg, not the household's. The family router keeps its job. A hung firewall costs the lab its internet, not the family theirs.

**Scope discipline.** Sentry Gate runs a firewall and nothing else. Password vault, monitoring, file sharing, and attack targets all moved to other hardware. That single decision is what makes a 3GB machine from 2008 a reasonable choice rather than a compromise.

**Prove the way back in before closing the door.** Remote access was installed and verified from off-network *before* any change that could remove local access.

**Verify institutional and physical constraints before buying hardware.** Housing policy killed a dorm firewall plan. Discontinued residence-hall ethernet killed a dorm server. Both were confirmed before money was spent.

---

## Roadmap

**Immediate (no new hardware):** DNS hardening in Unbound, hostname and NTP, config backup routine.

**On second NIC:** WAN/LAN interface split, default-deny ruleset, Suricata in IDS mode before IPS.

**On server acquisition:** powerline link, hypervisor install, RAID1 before any real data, service migration.

**Planned projects:** two-site Wazuh detection pipeline, remote red-to-blue exercise across the mesh link, public cloud honeypot with capture analysis.
