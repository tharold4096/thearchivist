- MoCA — only revisit if powerline underperforms in practice
---
 
## Key learnings
 
- **Policy and physical constraints before architecture.** UNT housing killed the dorm router; discontinued residence-hall ethernet killed the dorm server. Both were confirmed before hardware was bought. Verify institutional and physical constraints first.
- **Old hardware fails in ways that masquerade as software problems.** A failing 500GB drive caused Pi-hole install hangs. A GPT partition table caused a "dead keyboard." Neither symptom pointed at the real cause. When something behaves impossibly, question the layer below the one you're looking at.
- **Diagnostic tests that don't test what you think.** "I tried MBR in Rufus" was a false negative — DD mode ignores that setting. Booting Ubuntu successfully was the *good* test, because it isolated one variable cleanly.
- **When the hang happens matters more than what hangs.** Freezing at the BIOS splash, before any OS code runs, ruled out "OPNsense doesn't support this hardware" instantly. Timing is diagnostic information.
- **Scope discipline beats capability stacking.** Sentry Gate does one thing. That decision is what makes a 3GB 2008 machine a reasonable choice rather than a compromise.
- **Blast radius as a design principle.** Family LAN untouched, family router untouched, failures confined to the server's leg. This constraint has produced better architecture than "what's technically possible" would have.
- **Prove the way back in before closing the door.** Tailscale verified *before* the interface split, not after.
- **Drive health is foundational.** SMART before assigning any role to old hardware. Verify flash capacity before trusting it (H2testw/F3).
- **Alternatives worth knowing if OPNsense ever fails on this hardware:** IPFire (Linux, web UI, runs comfortably on 2GB), VyOS (Linux, CLI-driven, enterprise-credible), OpenWrt x86, or plain Debian + nftables + Suricata. **pfSense is not an escape hatch** — same FreeBSD base, same boot media behavior.
