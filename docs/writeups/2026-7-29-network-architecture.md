# Network Architecture and Design Decisions

The technical shape of this lab was determined more by constraints than by preference. This documents what was decided, what was rejected, and the reasoning — including the things deliberately left out.

---

## Constraints that drove the design

| Constraint | Consequence |
|---|---|
| University housing bans personal routers and network switches | No network hardware at the dorm; remote access must be outbound-only |
| Residence-hall ethernet discontinued | Servers cannot live at the dorm — no wired uplink, and servers have no wireless radio |
| Family network must not be disrupted | Firewall sits on one machine's leg, not the household's; family router untouched |
| Target location has no ethernet drop | Ethernet-over-existing-wiring required |
| Firewall hardware is a 3GB machine from 2008 | One job only; everything else moves elsewhere |

---

## Blast radius as the organising principle

Every architectural decision was evaluated by asking what breaks when the component fails.

**The firewall sits inline on the server's network leg only.** The family's devices connect to their router as they always have. They don't route through the firewall, don't see its subnet, and are unaffected if it hangs. A failure costs the lab its internet access — a problem to fix at leisure, not a household emergency.

This ruled out a design that was seriously considered: bridging the modem and having the firewall replace the family router entirely, taking a public address and filtering all household traffic. It's a stronger project on paper. It was rejected because:

- Blast radius expands from one machine to every device in the house
- It requires access to family-owned infrastructure and possibly an ISP call
- It places genuine internet-facing attack surface on the WAN interface
- Many residential ISPs use CGNAT, which would prevent obtaining a routable address at all — worth confirming before the idea is even viable

Kept as a separate future project rather than folded into this one. Every decision here has had a deliberately small blast radius; that would have been the first to break the pattern.

---

## Topology

```
Home router ──► powerline ──► Firewall WAN ─┐
(family LAN,                                │  filtering
 untouched)                Firewall LAN ────┴──► Server
```

Everything else runs over the mesh VPN, which is indifferent to physical topology: the dorm workstation, the firewall, the server, mobile devices, and eventually a cloud honeypot.

---

## Addressing

| Segment | Range | Notes |
|---|---|---|
| Family LAN | `192.168.1.0/24` | Untouched. Router at `.1`. |
| Firewall WAN | `192.168.1.x` | DHCP client of the family router, like any other device |
| Firewall LAN | `192.168.10.0/24` | Dedicated to the server |
| Server | Static on the firewall's LAN | Stable target for rules and VPN routes |
| Mesh VPN | `100.64.0.0/10` | Overlay, independent of physical topology |

### The DHCP hazard

OPNsense ships defaulting to `192.168.1.1` with a DHCP server enabled. Connecting that to a typical home network without changing it produces two simultaneous failures: an address collision with the router, and a second DHCP server handing out leases with a gateway that goes nowhere.

The resulting symptom — internet failing intermittently for whichever household member happens to get the wrong lease — is miserable to diagnose and lands on people who didn't opt into the project.

**Verify DHCP is disabled before any cable reaches a shared network.** During staging, the firewall was given a static address well outside the router's DHCP pool, with its own DHCP server explicitly off.

---

## WAN configuration notes

**WAN connects to the router, not the modem.** It takes an ordinary private address like any other client. The modem is not touched.

**No bridge mode.** Double NAT is acceptable here specifically because the remote-access design is outbound-only and needs no port forwarding at either layer. The usual objection to double NAT — inbound port forwarding becoming painful — doesn't apply to a design that never forwards ports.

**"Block RFC1918 Private Networks" must stay off.** The option assumes the WAN interface sits on public address space, where private-range source traffic is inherently bogus. Here the WAN is on a private network by definition, so enabling it blocks the upstream. The failure mode is nasty: everything appears correctly configured and nothing reaches the internet.

**"Block bogon networks" can stay on.** Harmless behind a router, marginally useful.

---

## DNS hardening

Design decided, implementation pending. Scope note: this applies to the server segment behind the firewall, not to household devices — extending it house-wide would mean pointing the family router at this resolver, which reintroduces the blast-radius problem.

### Baseline

- **DNSSEC validation on.** This is the actual security control — response integrity and resistance to cache poisoning. Everything else below is privacy, which is a different property.
- **WAN DHCP resolver override off.** Otherwise the upstream router silently replaces the configured resolver with the ISP's, undoing the rest of this.
- **ISP resolvers rejected.** They log, they sometimes hijack NXDOMAIN responses, and they're the one party in the chain that can't be audited.

### Recursion vs. forwarding

Two defensible models with different threat assumptions:

**Full recursion** resolves from the root servers down with no upstream forwarder. No third party observes the query stream because there isn't one. Cold lookups are marginally slower, and queries still travel unencrypted to authoritative servers.

**DoT forwarding** encrypts queries to a chosen upstream. The ISP learns nothing; the upstream learns everything. This trades diffuse exposure for concentrated exposure to a single chosen party.

**Recursion was chosen**, consistent with the self-hosting pattern used elsewhere in the project. If forwarding is ever wanted, a privacy-respecting resolver that validates DNSSEC is the appropriate pick.

### Enforcement

Configuring a resolver and *controlling* DNS on a segment are different things. Devices and VMs frequently hardcode public resolvers and ignore what DHCP tells them.

**NAT-redirecting port 53 on the LAN interface** forces everything behind the firewall onto the local resolver regardless of its own configuration. This is the step that turns a setting into an actual control.

### Known limitation: DoH

Encrypted DNS over HTTPS on port 443 is indistinguishable from ordinary web traffic and bypasses port-53 redirection entirely. Blocking known endpoint addresses is an arms race, not a solution.

Documented here rather than glossed over — knowing where a control's boundary lies is more useful than claiming it doesn't have one.

### Side effect

The resolver's native blocklist support covers what a separate DNS-filtering service would have provided. That service was dropped from the plan at no functional cost — a direct payoff from the decision to keep the firewall's scope narrow rather than stacking capabilities onto it.

---

## Physical layer: getting ethernet to the closet

The chosen location has no ethernet drop. Options compared:

| Option | Throughput | Dependency | Verdict |
|---|---|---|---|
| Powerline | ~300–600 Mbps real-world | Two wall outlets | **Chosen** |
| MoCA | ~1 Gbps, more consistent | Coax jack spliced onto the shared run | Rejected on risk |
| Cable run + switch | Full gigabit | Visible cabling through shared space | Fails the no-disruption constraint |

MoCA performs better. It was rejected because older cable installations often charged per room and left some jacks physically unconnected — an unknown that can't be resolved without testing, where being wrong wastes the hardware. Powerline has no equivalent dependency.

**AV2000 over AV1000:** real powerline throughput is a large, wiring-dependent discount off the rated figure. The premium buys headroom against an unknown, not speed the workload will use.

**Placement rules:** direct wall outlets at both ends — never power strips or surge protectors, which filter the signal — and the same electrical circuit where possible.

---

## Scope discipline

The firewall runs a firewall. Nothing else.

Everything originally slated for this hardware — password vault, uptime monitoring, DNS filtering as a separate service, file sharing, backup repository, and a deliberately vulnerable attack target — moved to the server instead.

This wasn't a capability cut. A 3GB Core 2-era machine running an IDS in inline blocking mode is fully occupied by that one job. The decision to stop stacking services is what makes fifteen-year-old hardware a *reasonable* choice for this role rather than a compromise being justified after the fact.

---

## Deferred deliberately

| Item | Why |
|---|---|
| Whole-house router replacement | Different blast radius, different project |
| MoCA | Only if powerline underperforms in practice |
| House-wide DNS filtering | Would require pointing the family router at this resolver |
| Boot drive mirroring | Lower priority than mirroring bulk storage |

---

## Pending

- Second NIC — blocks the WAN/LAN split and everything downstream of it
- Suricata, **starting in alert-only mode for roughly a week** before enabling inline blocking, so that a rule breaking legitimate traffic is diagnosable rather than mysterious
- Default-deny outbound ruleset from the server segment
- Key-only SSH
- UPS — upgraded from optional once the firewall became a single point of failure for the server's connectivity, since an unclean shutdown mid-write risks both the firewall's configuration state and any running VMs
