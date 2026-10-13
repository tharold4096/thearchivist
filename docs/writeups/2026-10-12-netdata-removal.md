# Netdata Removal (thearchivist host)

**Date:** 2026-10-12
**Machine(s):** thearchivist (Proxmox host, 192.168.10.202); Caddy (CT 103)
**Status:** Complete
**Tags:** monitoring, hardening, attack-surface reduction, cleanup

---

## Why I built this

* Netdata 2.12.1 was installed natively on the Proxmox host from Netdata's own apt repo, and I never used it.
* It served an unauthenticated dashboard on `0.0.0.0:19999` (allowed from `localhost 192.168.10.*`) and was also reverse-proxied at `netdata.home.arpa`. Its plugins included `systemd-journal`, `apps`, `network-viewer` and eBPF, so anyone on the LAN could see host processes, connections and logs.
* It auto-updated as root from a third-party repo and loaded eBPF programs into the host kernel.
* Cost: ~466 MiB RAM, ~19% of one core averaged over the day before removal, 2.1 GB of dbengine metrics in `/var/cache/netdata`.
* CheckMK (CT 115, 192.168.10.215) is taking over host and guest monitoring. Its 1-minute checks cover everything I'd actually act on. The one thing it can't replace is Netdata's per-second, kernel-level detail, which I wasn't using.

## How I built it

* **Dry run first:** `apt-get -s purge 'netdata*'` listed exactly 19 Netdata packages and nothing else. I didn't run autoremove, because the orphaned libs and old `proxmox-kernel-7.0.14-*` images it lists are a separate cleanup.
* **Backup:** I tarred `/etc/netdata` and copied the Caddyfile off-host before making changes.
* **Host:**
  * `systemctl stop netdata`
  * `apt-get purge -y 'netdata*'`
  * removed the leftover `/var/cache/netdata`, `/var/lib/netdata`, `/var/log/netdata`, `/etc/netdata` and `/usr/lib/netdata` (dpkg leaves non-empty directories behind)
  * deleted `/etc/apt/sources.list.d/netdata.sources`
  * `userdel netdata` (the `netdata-user` purge leaves the account behind; `find / -xdev -user/-group netdata` came back empty first)
* **Caddy (CT 103):**
  * backed up the file to `/etc/caddy/Caddyfile.bak-20261012`
  * removed the `netdata.home.arpa { reverse_proxy 192.168.10.202:19999 }` block
  * `caddy validate` reported a valid config before `systemctl reload caddy`

## What broke

* **Issue: purge left state behind**
  Symptom: dpkg warned that `/etc/netdata` and `/var/log/netdata` weren't empty, and `getent passwd netdata` still returned uid 988 after the purge.
  Root cause: Debian purge doesn't remove runtime-created files or system users.
  Fix: removed the directories by hand, checked that the user owned no files, then ran `userdel`.

## What worked

* `dpkg -l | grep -ci netdata` returns `0`, and `pgrep netdata` finds no processes.
* `ss -ltn | grep 19999` prints nothing, so the port is closed.
* The Netdata apt source is gone and the `netdata` user and group no longer exist.
* Caddy validates, is `active`, and has no `netdata` entries.

## What I'd do differently

* Not install a whole-host agent "just to see" without a plan to use it. It ran for weeks with LAN-wide access to the journal.

## Follow-ups

* If Sentry has a host override for `netdata.home.arpa`, it now points at nothing and can be deleted.
* Enrol the host with a CheckMK agent (and the Proxmox VE special agent) so host coverage doesn't stay a gap.

---

## Resume-ready summary

* Retired an unused, LAN-exposed Netdata agent from a Proxmox hypervisor after a dry-run-verified purge. This removed an unauthenticated journal and process dashboard, a third-party root auto-update channel and kernel eBPF hooks, and recovered ~0.5 GB RAM, ~0.2 core and 2.1 GB of disk ahead of a move to CheckMK.
