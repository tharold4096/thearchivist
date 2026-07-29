# Build Log

Chronological record of work, grouped by session. Each entry notes what was decided, what was ruled out, and why.

---

## Session 1 — July 28, 2026

### Phase 1 — Enterprise server proposal and siting

A decommissioned server became available through work: full RAM loadout, CPUs, redundant PSUs, no storage. Not yet confirmed — coworkers have done the same acquisition, but nothing is in hand.

**The question that mattered most was where it could physically live.** The dorm was preferred but ruled out on a hard technical constraint rather than a policy one: residence-hall ethernet was discontinued the previous fall. Enterprise servers ship with onboard NICs and no wireless radio, and running a server's entire workload over a USB WiFi adapter is not a serious foundation — unreliable drivers, unstable throughput, and no clean troubleshooting path on a headless box.

A secondary constraint reinforced it. Bridged VM networking would give each guest its own MAC and IP on the campus network, which is structurally close to the router behavior the housing policy targets and which the per-device registration portal is built to catch.

**Outcome:** the server goes home. This is not a compromise — it's the only viable siting.

### Phase 2 — Getting ethernet to the closet

The chosen location was a home closet: out of the way, quiet-adjacent, no family involvement. It has no ethernet drop. Three options were considered.

| Option | Verdict |
|---|---|
| Powerline (ethernet over electrical) | **Chosen** — no dependency on unknowns, two wall outlets |
| MoCA (ethernet over coax) | Faster and more stable, but depends on the closet's coax jack being spliced onto the shared run |
| Long cable run + switch | Best performance, but visible cabling — fails the "don't disrupt the household" constraint |

MoCA was the better performer on paper. It was rejected on risk: older cable installs frequently charged per room and left some jacks physically unconnected. That can't be resolved without testing, and a dead jack means the adapters are wasted. A free test using the existing cable modem as a signal source was designed but deprioritized once powerline proved sufficient for the workload.

**AV2000 was chosen over AV1000.** Real-world powerline throughput is a large and unpredictable discount off the rated figure, driven by wiring quality. The ~$20 premium buys headroom against that unknown, not speed that will ever be used — the workload is log shipping, SSH, and container pulls, none of which approach even the low end of the range.

**A household objection was raised and worked through.** Concerns about powerline fell into three categories: neighbor data leakage over a shared transformer (mitigated — modern adapters use AES with deliberate pairing, and the scenario largely doesn't apply to detached homes), power draw (2–6W per adapter, negligible), and RF interference with amateur radio or AM reception. The third is the only one with real substance, and it was flagged as something to ask about directly rather than reassure past.

### Phase 3 — Storage planning

Two drives were already on hand or ordered: a 240GB SATA SSD and a healthy 1TB HDD, both originally allocated to the Inspiron. Both were reassigned to the server.

**Redundancy priority was set as HDD before SSD.** Losing the boot SSD costs a hypervisor reinstall — annoying but bounded. Losing the bulk drive costs every VM's data. A second 1TB-class drive for a RAID1 mirror became the priority purchase, with the rule that nothing worth redoing lands on the array until the mirror exists.

An HDD for bulk VM storage was accepted as a genuine stopgap, not a permanent answer. Multiple guests doing random I/O against one spinning disk manifests as everything feeling slow simultaneously rather than one workload being slow.

**Deferred until hardware is in hand:** chassis form factor and its noise implications (tower servers idle around 30–40 dB(A); rack-mount 1U/2U units can hit 60–70+ under load), OEM drive caddy requirements, and whether the RAID controller can flip to HBA/passthrough mode.

### Phase 4 — Repurposing the Inspiron

With the server taking over as the core node, the Dell Inspiron 530 needed a new job. Four directions were considered:

- **Watchtower** — passive monitoring and detection, nothing depends on it
- **Bastion** — hardened jump host and mesh VPN entry point
- **Inline firewall** — sits in the traffic path, real blocking capability
- **Tripwire** — deliberately expendable honeypot or canary host

**Inline firewall was chosen**, with the single-point-of-failure risk explicitly accepted. This reversed an earlier decision that the machine needed no NIC upgrade — inline operation requires two interfaces, so a PCIe NIC went back into the budget.

The machine was renamed `sentrygate`. The name it previously carried, `thearchivist`, transferred to the incoming server.

**Scope was deliberately constrained to firewall duty only.** Everything the Inspiron had been slated for — password vault, uptime monitoring, DNS filtering, file sharing, backup target, attack target — moved to the server. A 3GB Core 2-era machine running Suricata in IPS mode is fully occupied by that one job. This is the decision that makes the hardware choice reasonable rather than marginal.

**OPNsense was chosen over pfSense** for continuity with earlier planning and slightly more native Suricata IPS integration. The two are near-identical in capability and share a FreeBSD base — a fact that became relevant later.

### Phase 5 — Boot media troubleshooting

Getting OPNsense onto the machine took several failed attempts and was the longest single debugging sequence in the project. Full writeup: [`opnsense-legacy-bios-boot.md`](opnsense-legacy-bios-boot.md).

Summary: the 2008-era legacy BIOS hung at POST when presented with GPT-partitioned boot media, and the hang took USB keyboard emulation down with it. The MBR-partitioned `nano` image booted without issue.

A separate finding along the way: a suspiciously high-capacity USB drive was tested for counterfeit firmware using H2testw. It verified as genuine — but was still rejected as boot media because its USB 3.0 controller caused independent enumeration problems on this chipset.

### Phase 6 — First boot and initial configuration

OPNsense 26.7 came up on VGA console, contradicting the assumption that the nano image is serial-only.

Configured in this session:
- Root password changed from default
- Single NIC (`em0`) assigned as LAN, static addressing
- **DHCP server disabled** — critical, since OPNsense defaults to `192.168.1.1` with DHCP on, which would have collided with the family router's address and put a rogue DHCP server on their LAN
- Web GUI reachable from a machine on the family network for staging

An addressing choice was made to keep the box reachable from a desktop elsewhere in the house during setup. This access path is temporary and closes by design when the interfaces split — the family network becomes the WAN side at that point, and GUI access from WAN is blocked by default.

### Phase 7 — Network design decisions

Several questions were resolved that shape the eventual topology:

**WAN plugs into the home router, not the modem.** The firewall takes an ordinary private address like any other client on the network.

**No bridge mode on the family router.** Double NAT is acceptable here specifically because the entire remote-access story is an outbound-only mesh VPN that needs no port forwarding at either layer.

**A whole-house router replacement was considered and deliberately deferred.** Bridging the modem and having the firewall take a public IP is a genuinely strong project, but it changes the blast radius from "the lab server" to "the entire household," requires access to family infrastructure, and puts real internet-facing attack surface on the WAN side. Many residential ISPs also use CGNAT, which would prevent obtaining a routable address at all. Kept as a separate future project rather than a modification of this one.

**A configuration trap was documented ahead of time:** "Block RFC1918 Private Networks" must stay off. The option assumes WAN sits on public address space; here it will sit on a private network by definition, and enabling it blocks the upstream. The failure mode — everything configured correctly, nothing reaching the internet — is hard to diagnose.

### Phase 8 — DNS hardening plan

Design decided, implementation pending. Details in [`network-architecture.md`](network-architecture.md).

Key choices: DNSSEC validation on (the actual integrity win, as distinct from the privacy measures), full recursion preferred over DoT forwarding to avoid concentrating query visibility in a single upstream, ISP resolvers rejected, and the WAN DHCP override disabled so the family router can't silently replace the resolver configuration.

Unbound's native blocklists were found to cover what a separate DNS-filtering service would have provided, which retroactively justified dropping that service from the plan at no cost.

The DoH limitation was documented honestly rather than papered over: encrypted DNS over 443 is indistinguishable from ordinary HTTPS and bypasses port-53 redirection. Blocking known endpoint addresses is an arms race, not a fix.

### Phase 9 — Remote access

Tailscale installed on the firewall and verified working from outside the home network. Full writeup: [`remote-access-tailscale.md`](remote-access-tailscale.md).

Two non-obvious obstacles were hit and resolved: the plugin does not assign its own network interface, and firewall rules cannot be created for an unassigned interface. Once assigned, a correct-looking pass rule still silently dropped all traffic — debugged through the live firewall log to the alias table.

Access was then tightened from a blanket allow to an explicit host allowlist.

### Phase 10 — Verification

Config backup exported off the device. Full reboot performed while console access was still physically available, confirming that the GUI and the mesh VPN connection both come back unattended.

This last step was deliberate: several changes in this session touched interface assignment and plugin authentication, and discovering a failure to auto-start from a different city, with no console access, would have been considerably worse than spending five minutes confirming it locally.

---

## Reusable lessons

**Timing is diagnostic information.** A hang at the BIOS splash, before any OS code executes, instantly ruled out operating-system compatibility as a cause. *When* something fails narrows the search more than *what* fails.

**Some tests don't test what they appear to.** Selecting "MBR" in an imaging tool has no effect on a raw disk-image write — the partition table comes from inside the image. That produced a false negative that pointed the investigation away from the real cause.

**Absence of a block is not permission.** A default-deny firewall drops anything not explicitly permitted. An interface with no rules is not "open by default with nothing blocking it."

**Configuration that looks correct may not be loaded.** A firewall alias can display exactly the right contents in its edit form while its underlying table is empty. The diagnostic view showing what the packet filter actually loaded is a different thing from the configuration view, and only one of them reflects reality.

**Old hardware fails in ways that impersonate software problems.** A failing drive produced installer hangs. A partition table produced a dead keyboard. Neither symptom pointed at its own cause.
