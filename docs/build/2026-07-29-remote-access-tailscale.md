# Remote Access: Mesh VPN to an OPNsense Firewall

Goal: administer the firewall — and eventually the server behind it — from anywhere, without opening a single inbound port on the home router.

Getting there required working around two behaviours that aren't obvious from the plugin's interface, and debugging a firewall rule that was correct in every visible respect while silently dropping all traffic.

> \\\\\\\\\\\\\\\*\\\\\\\\\\\\\\\*Note on addresses.\\\\\\\\\\\\\\\*\\\\\\\\\\\\\\\* Tailnet addresses in this document are redacted. They aren't internet-routable, but publishing a live map of which address belongs to which device is unnecessary detail for a public repo.

\---

## Why a mesh VPN rather than port forwarding

The constraint that shaped this was a university housing policy prohibiting personal routers and network switches, combined with a per-device registration portal on the campus network. Anything requiring inbound connectivity or additional network hardware was ruled out at the dorm end.

A mesh VPN sidesteps this entirely. Connections are **outbound-only** from every node, so nothing needs forwarding at either NAT layer. The same property that satisfies the housing policy also makes double NAT a non-issue at the home end — which is why the family router keeps its normal configuration instead of being bridged.

\---

## Sequencing: prove the way back in before closing the door

The firewall's administrative interface is currently reachable from a machine on the family network. **That access path closes by design** once the WAN/LAN split happens: the LAN moves to its own subnet facing only the server, the family network becomes the WAN side, and GUI access from WAN is blocked by default.

So the ordering matters:

1. Install and authenticate the mesh VPN **while local access still works**
2. Verify remote reachability **from outside the home network**
3. Only then split the interfaces

Doing this in the opposite order — splitting first, arranging remote access afterward — is the standard way to end up locked out of a headless box in another building.

**Verify from cellular, not home WiFi.** Testing from a phone on the same WiFi can succeed via the local network while the mesh path is entirely broken, producing false confidence at precisely the wrong moment.

**Fallbacks, in order:** a laptop plugged directly into the firewall's LAN port sits on the same subnet as the server and works whenever the VPN itself is the broken thing. Below that, VGA console and keyboard, which depend on no networking at all.

\---

## Obstacle 1: the interface isn't assigned

After installing the plugin and authenticating successfully, the firewall was visible in the mesh network's admin console and appeared healthy. Connections to its administrative interface timed out.

**The plugin creates its network interface but does not assign it within the firewall.** Until it's assigned, the default policy blocks all incoming tunnel traffic to the host — web UI, SSH, and ICMP alike — and firewall rules cannot be created for it, because there's no interface tab to create them on.

This has been raised more than once as a bug against the plugin. The fix:

1. Interfaces → Assignments → select the tunnel device from the dropdown → add
2. Enable the interface, give it a description (this becomes its firewall tab name), leave IP configuration as none — the VPN manages its own addressing
3. Apply, then create rules on the newly available tab

A second, separate gate exists beyond the firewall: the administrative service's own listen interfaces. If bound to specific interfaces rather than all, the tunnel interface must be included or the service won't answer even with the firewall fully open.

\---

## Obstacle 2: absence of a block is not permission

The next failure was more instructive. With the interface assigned and a pass rule in place, traffic was still being dropped.

The reasoning that delayed the fix was: *there are no rules blocking this, so it should pass.* That's backwards for a default-deny firewall. An interface with no matching rule blocks everything. The only reason the LAN interface behaves permissively is a built-in anti-lockout rule, which exists on LAN and nowhere else.

\---

## Debugging a rule that looks correct

At this point the rule was, by inspection, correct: right interface, direction In, action Pass, protocol any, source set to an alias containing the client addresses, destination any. Traffic was still hitting the default deny.

The live firewall log entry:

```
Interface : TailscaleVPN
Direction : In
Protocol  : TCP
Source    : 100.x.x.x:60950
Destination: 100.x.x.x:443
Action    : block
Rule      : Default deny / state violation rule
```

**What this eliminated.** The interface was right — traffic was arriving on the tunnel interface and being evaluated there, which also disproved a suspected plugin bug where tunnel traffic bypasses rule evaluation entirely. The direction was right. The protocol matched. The destination was the firewall on 443, as intended. IPv4, so the rule's address-family setting wasn't the issue.

**What remained.** A packet that should match the rule on every field, hitting the default deny instead. Only two explanations survive that: the rule isn't in the loaded ruleset, or the alias it references is empty.

**It was the alias.** An alias can display exactly the right contents in its edit form while the table the packet filter actually loaded is empty. The configuration view and the runtime view are different things, and only one of them determines behaviour. `Firewall → Diagnostics → Aliases` shows the loaded table — that's the authoritative view, and checking it earlier would have saved most of the session.

**One observation that looked like a symptom but wasn't:** two simultaneous outbound source ports from each client. That's ordinary browser behaviour — parallel TCP connections to the same host — and had nothing to do with the failure.

\---

## Hardening: from blanket allow to explicit allowlist

The rule that first worked permitted any source on the tunnel interface. That grants administrative access to **every device on the mesh network, present and future** — including anything added later for an unrelated reason.

Tightened by creating a host alias containing only the two devices that should have admin access, and changing the rule's source from `any` to that alias.

Two things learned building it:

* **Alias names cannot contain spaces.** Letters, numbers, and underscores only.
* **Interface network macros are not host addresses.** Auto-complete offers entries referring to an interface's own network, which will not match traffic from client devices.

**The tradeoff:** mesh addresses are stable per device, but a device that's removed and re-added — or an app reinstalled — can return with a different address and be locked out by its own rule. This is worth remembering as a cause when remote access mysteriously stops working after unrelated maintenance. The console and direct-LAN fallbacks remain unaffected.

**Next layer, not yet implemented:** the mesh provider's own ACLs can enforce the same restriction before traffic ever reaches the firewall. Defence in depth rather than a replacement.

\---

## Verification

* Administrative interface reachable over the tunnel from a mobile device **on cellular data**, confirming genuine off-network access
* Configuration exported off the device — the boot media is a consumable, and an exported config turns a failure into a short rebuild
* **Full reboot performed while console access was still physically available**, confirming both the web interface and the tunnel come back unattended

That last step was deliberate. The session had changed interface assignment, firewall rules, and plugin authentication. Discovering an auto-start failure remotely, with no console, would have been considerably worse than five minutes of local verification.

\---

## Planned: subnet routing

Not yet implemented — it's gated on the second NIC, since the subnet in question doesn't exist until the interface split happens.

The firewall will advertise the server's subnet to the mesh network, making every device behind it reachable from any node without needing its own VPN client. Requires IP forwarding enabled and approval of the advertised route in the admin console.

**A detail that caused confusion:** the route approval interface is contextual, not a fixed menu item. It appears only after a node advertises a route, so looking for it beforehand finds nothing.

**A deliberate omission:** the firewall will not advertise the family's subnet, even though it currently sits on it. Doing so would route mesh traffic into the household network — scope creep against the containment principle the whole design rests on — and would conflict badly with any other network using the same common address range.

