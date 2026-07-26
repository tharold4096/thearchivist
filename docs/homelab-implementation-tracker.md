# Homelab Implementation Tracker

A running list of everything planned, in progress, or deployed across the lab. Each machine gets its own table using the same columns, so a new item just means a new row — no reformatting needed as the project grows. A blank copy-paste template is at the bottom for anything that needs more room than a row (longer notes, multi-step config, etc.).

**Status legend:** Planned · In Progress · Deployed · Deprecated

\---

## Arch (Dell Inspiron 530 — home)

|Component|Status|Drive|RAM (idle / peak)|Purpose|
|-|-|-|-|-|
|Pi-hole|Planned|SSD|\~50–80MB / —|DNS filtering, home network|
|Vaultwarden|Planned|SSD|\~15–30MB / —|Self-hosted password manager|
|Uptime Kuma|Planned|SSD|\~120–180MB / —|Status/alerting dashboard, watches both sites|
|Wazuh agent|Planned|SSD|\~80–120MB / —|Ships logs to Tower's Wazuh manager over Tailscale|
|Juice Shop|Planned|SSD|\~200–300MB / —|Remote attack target for red/blue exercises|
|Samba|Planned|HDD (TBD: shared or dedicated)|\~20–50MB / \~100–150MB|Family file share, access-control practice|
|Borg|Planned|HDD|\~10–20MB / spikes during run|Nightly off-site backup of Tower's configs + SIEM data|
|fail2ban + hardened SSH|Planned|SSD|\~10–20MB / —|Bastion-host hardening, admin-only access|
|Tailscale|Planned|SSD (system-level)|\~10–20MB / —|Mesh VPN link back to Tower|
|Swapfile (2–4GB)|Planned|SSD|N/A (safety net, not a service)|Prevents OOM kills under load|
|*(new item)*|||||

\---

## Tower (Gaming PC — dorm)

|Component|Status|Location|RAM allocation|Purpose|
|-|-|-|-|-|
|AD environment (Windows Server + clients)|Planned|VM|Several GB per VM|Core AD attack-chain lab|
|Wazuh manager|Planned|VM or host|—|Central SIEM, receives logs from both sites|
|Kali Linux|Planned|VM|—|Attacker box, local + across Tailscale|
|Metasploitable2/3, DVWA, Juice Shop (local)|Planned|VM|—|Local vulnerable targets|
|Sysmon + Windows Event Forwarding|Planned|Host/VM|—|Host-level logging|
|*(new item)*|||||

\---

## Oracle Cloud VM (honeypot)

|Component|Status|Location|RAM allocation|Purpose|
|-|-|-|-|-|
|Cowrie or T-Pot|Not started|Oracle Always Free tier|Per free-tier instance limits|Public honeypot, attacker IP/technique analysis|
|*(new item)*|||||

\---

## Blank entry template

Copy this block when a new item needs more detail than a table row:

```
### \[Component Name]
- Status: Planned / In Progress / Deployed / Deprecated
- System: Tower / Arch / Cloud VM / other
- Drive: SSD / HDD / N/A
- RAM cost: idle \~\_\_\_ , peak \~\_\_\_
- Purpose:
- Notes:
```

