---
title: "Wazuh agents across the LXC fleet"
date: 2026-09-18
type: build
status: complete
hosts: [thearchivist, ct104-wazuh, ct100-jellyfin, ct102-ntfy, ct103-caddy, ct107-dns-audit, ct108-immich, ct200-vaultwarden]
tags: [siem, wazuh, lxc, hardening]
summary: "Enrolled 13 unprivileged containers as version-pinned Wazuh agents in three risk-tiered groups, so logins, service logs, FIM and package CVEs inside every LXC reach the SIEM."
verified: 2026-11-12
open: 3
---

# Wazuh agents across the LXC fleet

## At a glance

| | |
|---|---|
| **Goal** | See inside containers the host agent can't |
| **Stack** | Wazuh 4.14.7 agents, held packages, `pct push`/`pct exec`, agent groups by tier |
| **Hosts** | 13 LXCs on thearchivist → manager CT 104 (192.168.10.204) |
| **Entry points** | Agents → 192.168.10.204:1514 |
| **Result** | Agents 004–016 Active on rollout day; SSH disabled on Vaultwarden |
| **Config** | hosts/lxc/ct104-wazuh/lxc-agents/wz-enroll.sh |

> **Current state (verified 2026-11-12):** Survives power cycles: 2026-11-12 `agent_control -l` shows all running CTs Active; 007 dns-audit and 013 flaresolverr are Disconnected because those CTs are stopped. **Not enrolled:** CT 115 checkmk, CT 116 responder, VM 106 budget, VM 150 pbs. Agent **015 `actualbudget`** is a stale entry from the retired Actual Budget build and should be removed.

## Context

Before this, only the manager (CT 104), Sentry Gate, the Archivist host and samba-vm reported to Wazuh. The host agent can't see inside unprivileged containers, so logins, service logs, file integrity and package vulnerabilities in every LXC went unrecorded. That includes Vaultwarden, the Caddy CA and the internet-facing arr apps.

## What was built

* **Tools/stack:** Wazuh 4.14.7 (manager and agents version-matched), `pct push` / `pct exec`.
* **Scope (audit, 2026-09-18):**
  * **Tier 1:** exposed to untrusted input, holds secrets, or guards the security tooling.
  * **Tier 2:** web-exposed or holds personal data.

| Group | CTs | Rationale |
|---|---|---|
| `lxc-edge` | 102 ntfy, 103 caddy, 200 vaultwarden, 107 dns-audit | Alert channel, TLS front door + internal CA, the vault, the accountability control |
| `lxc-arr` | 109 seerr, 110 prowlarr, 111 sonarr, 112 radarr, 113 qbittorrent, 114 flaresolverr | Untrusted external input (indexers, swarm, headless Chromium); API keys |
| `lxc-data` | 100 jellyfin, 106 actualbudget, 108 immich | Personal/financial data, exposed through Caddy |

* **Deliberately not enrolled:**
  * CT 104: the manager already monitors itself as agent 000.
  * VMs 210/211: the vulnerable lab range. Enrolling it would pollute production alerts and give a compromised range a path to the manager and its enrollment password.
  * CT 105 (nuclei-scanner): on-demand offensive tooling, so mostly noise.
* **Deferred:** the Omarchy laptop, Tower and the Parrot VM. Not in scope yet.
* **Key steps:**
  * Created the groups with `agent_groups -a`.
  * Piloted on ntfy and confirmed Active before rolling through the rest one at a time, stopping on the first failure.
  * Each CT gets the host's Wazuh keyring and repo, `wazuh-agent=4.14.7-1`, and `apt-mark hold`, so an agent can never run ahead of the manager. See the version-pin gap in `2026-09-15-homelab-update-guest-coverage.md`.
* **Enrollment secret handling:**
  * The manager's `authd.pass` was copied to a mode-600 temp file on the host and pushed to each CT only for the duration of the install.
  * It was deleted in each CT right after enrollment (checked per CT), and the host copy was `shred`ded.
  * It never appeared in terminal output and is not in this repo.
* **Config/scripts:** [`wazuh-lxc-agents/wz-enroll.sh`](../../../hosts/lxc/ct104-wazuh/lxc-agents/wz-enroll.sh). It expects `/root/.wz-enroll.pass` on the host (`<SET-ON-HOST>`, sourced from CT 104 `/var/ossec/etc/authd.pass`).
* **Also, Vaultwarden sshd disabled:** `systemctl disable --now ssh.socket ssh.service` in CT 200. Management goes through the Proxmox console (`pct enter 200`).

## Issues hit

* **Issue: rootcheck warnings on the pilot**
  Symptom: `No rootcheck_files file: 'etc/shared/rootkit_files.txt'` (and the trojans equivalent).
  Root cause: groups created with `agent_groups -a` only get `agent.conf`. The signature files live in `shared/default/`.
  Fix: copied `shared/default/*.txt` into each new group's shared dir (owned `wazuh:wazuh`) before the rollout.
* **Unprivileged-LXC limit (not a failure):** auditd who-data isn't available in unprivileged containers, so FIM there is realtime/scheduled only, with no who-changed attribution.
* **Cosmetic:** CT 107 has no generated `en_US.UTF-8` locale, so apt/perl print locale warnings. Harmless.

## Verification

Verified 2026-09-18:

* `agent_control -l`: agents 004–016 all **Active**; group membership 4 / 6 / 3 as in the table.
* Every CT: `wazuh-agent 4.14.7-1`, held, service active, enrollment file removed.
* CT 113: WireGuard handshake fresh and qBittorrent active after the install. The agent reaches `.204` over `eth0`, which the VPN design already permits for the web UI.
* CT 200: `ssh.service` and `ssh.socket` disabled and inactive; `192.168.10.205:22` closed; `pct exec` works; `https://vaultwarden.home.arpa/alive` → 200.

**Still owed:** after the next power cycle, `pct exec 104 -- /var/ossec/bin/agent_control -l` should show 004–016 Active again. That's all 13 if 106 and 107 are running, otherwise 11, with 106 and 107 Disconnected.

## Follow-ups

Status as of 2026-11-12. Ticked items are closed; the evidence is in *Current state* above or the linked doc.

- [x] Agents come back Active after the nightly power cycle (2026-11-12).
- [ ] Enroll CT 115 checkmk, CT 116 responder, VM 106 budget and VM 150 pbs, or record why each is excluded.
- [ ] Remove stale agent 015 `actualbudget`: `pct exec 104 -- /var/ossec/bin/manage_agents -r 015`.
- [ ] Tune `agent.conf` per group (FIM on the Vaultwarden data dir and the Caddy CA).

## Lessons

* Tune `agent.conf` per group (FIM paths for the Vaultwarden data dir and the Caddy CA, arr config dirs) now that the groups exist. As it stands every group inherits the defaults.

---

## Resume line

* Audited a 15-container Proxmox fleet for SIEM coverage, then rolled out version-pinned Wazuh agents to 13 containers in role-based groups. Enrollment secrets never touched disk outside a transient root-only file.
* Reduced attack surface on the password-vault container by removing an unused SSH listener, keeping management on the hypervisor console.
