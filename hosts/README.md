# Hosts

Every machine in the lab, one folder each. The folder holds the host's summary (`README.md`) and every config fragment deployed on it. The same data in machine-readable form is [`inventory.yml`](inventory.yml); the website reads that file.

_All values read live on 2026-11-12. Arr-stack containers (CT 109–114) are documented locally only._

```text
hosts/
├── inventory.yml        machine-readable source of truth
├── physical/            sentrygate (firewall), thearchivist (Proxmox host)
├── lxc/ctNNN-name/      Proxmox containers, by VMID
├── vm/vmNNN-name/       Proxmox VMs, by VMID
└── clients/             admin laptop, dorm desktop
```

## Networks

| Network | CIDR | Gateway | Notes |
|---|---|---|---|
| Lab LAN (Sentry Gate LAN) | 192.168.10.0/24 | 192.168.10.1 | Static guests sit outside the DHCP pool. Proxmox bridge vmbr0. |
| Family LAN (home router) | 192.168.1.0/24 | 192.168.1.1 | Untouched by the lab. Sentry's WAN (bge0) is 192.168.1.223 on it; family devices never route through Sentry. |
| Isolated range (vmbr1) | — | — | Proxmox bridge with no physical port. Only range-gw and target-juice attach to it. |
| Tailscale tailnet | 100.64.0.0/10 | — | Remote admin path. Sentry advertises the lab LAN as a subnet route and offers an exit node. |

## Physical machines

| Host | ID | Address | Ports | Status | Role | Open |
|---|---|---|---|---|---|---|
| [sentrygate](physical/sentrygate/README.md) | — | 192.168.10.1/24 | 53, 67, 80, 123, 161, 443, 3493, 41641 | 🟢 running | Inline firewall, router, DNS filter and Tailscale subnet router for the lab LAN | 4 |
| [thearchivist](physical/thearchivist/README.md) | — | 192.168.10.202/24 | 111, 3128, 8006 | 🟢 running | Proxmox VE hypervisor running every lab service | 3 |

## LXC containers

| Host | ID | Address | Ports | Status | Role | Open |
|---|---|---|---|---|---|---|
| [ct100-jellyfin](lxc/ct100-jellyfin/README.md) | 100 | 192.168.10.207 | 8096 | 🟢 running | Media server (movies and TV) for the family |  |
| [ct102-ntfy](lxc/ct102-ntfy/README.md) | 102 | 192.168.10.203 | 80 | 🟢 running | Push-notification server; every alert in the lab ends here |  |
| [ct103-caddy](lxc/ct103-caddy/README.md) | 103 | 192.168.10.201 | 80, 443 | 🟢 running | Reverse proxy with an internal CA for every *.home.arpa name | 1 |
| [ct104-wazuh](lxc/ct104-wazuh/README.md) | 104 | 192.168.10.204 | 443, 1514, 1515, 55000 | 🟢 running | SIEM — Wazuh manager, indexer and dashboard | 1 |
| [ct105-nuclei-scanner](lxc/ct105-nuclei-scanner/README.md) | 105 | dhcp | — | ⚪ stopped | Vulnerability scanner (Nuclei), run on demand |  |
| [ct107-dns-audit](lxc/ct107-dns-audit/README.md) | 107 | dhcp | — | ⚪ stopped | DNS accountability — attests Sentry's blocking config and reviews DNS logs | 1 |
| [ct108-immich](lxc/ct108-immich/README.md) | 108 | 192.168.10.208 | 2283, 3003 | 🟢 running | Family photo library (Immich) |  |
| [ct115-checkmk](lxc/ct115-checkmk/README.md) | 115 | 192.168.10.215 | 80, 111, 8000 | 🟢 running | Monitoring — Checkmk Community, 17 hosts, alerts to ntfy and the responder | 3 |
| [ct116-responder](lxc/ct116-responder/README.md) | 116 | 192.168.10.216 | 8787 | 🟢 running | AI alert responder — Claude diagnoses Checkmk alerts, one-tap approved fixes; also categorizes Sure transactions | 2 |
| [ct200-vaultwarden](lxc/ct200-vaultwarden/README.md) | 200 | 192.168.10.205 | 8000 | 🟢 running | Password manager (Bitwarden-compatible) |  |

## Virtual machines

| Host | ID | Address | Ports | Status | Role | Open |
|---|---|---|---|---|---|---|
| [vm101-samba](vm/vm101-samba/README.md) | 101 | 192.168.10.120 | 139, 445 | 🟢 running | Family file server — four users, 100 GB quota each | 2 |
| [vm106-budget](vm/vm106-budget/README.md) | 106 | 192.168.10.206 | 3000 | 🟢 running | Personal finance — Sure (Rails) in Docker, SimpleFIN sync | 3 |
| [vm150-pbs](vm/vm150-pbs/README.md) | 150 | 192.168.10.220 | 8007 | 🟢 running | Proxmox Backup Server — datastore store1 on a passed-through 2 TB disk | 1 |
| [vm210-range-gw](vm/vm210-range-gw/README.md) | 210 | — | — | ⚪ stopped | Attack-range gateway between the lab LAN and the isolated vmbr1 |  |
| [vm211-target-juice](vm/vm211-target-juice/README.md) | 211 | — | — | ⚪ stopped | Deliberately vulnerable target (OWASP Juice Shop) on the isolated range only |  |

## Clients

| Host | ID | Address | Ports | Status | Role | Open |
|---|---|---|---|---|---|---|
| [omarchy](clients/omarchy/README.md) | — | 100.113.94.88 | — | 🟢 running | Admin laptop; DNS pinned to Sentry, homelab status bar widget | 1 |
| [towerofpower](clients/towerofpower/README.md) | — | 100.78.28.104 | — | ⚪ offline | Dorm desktop (48 GB) — AD lab, Kali and Parrot VMs |  |

_Ports column omits 22 (ssh) and 6556 (Checkmk agent), which most hosts have. Open = unresolved follow-ups on that host's page._

## Adding a host

1. Add an entry to `inventory.yml` (copy a sibling; read every value live).
2. Create `hosts/<group>/<slug>/README.md` from [`docs/templates/host.md`](../docs/templates/host.md).
3. Put every config you deploy on it in that folder, secrets as `<SET-ON-HOST>`.
4. Arr-stack hosts: name the folder with its arr token (`ct1NN-sonarr`) so `.gitignore` keeps it local, and add it to `inventory.arr-stack.yml` instead.
