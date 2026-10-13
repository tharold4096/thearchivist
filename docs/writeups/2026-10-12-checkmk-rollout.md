# CheckMK Rollout: Host, Guests, Firewall, Web UIs, Phone Alerts

**Date:** 2026-10-12
**Machine(s):** thearchivist (PVE host, 192.168.10.202); CT 115 checkmk (192.168.10.215); every running guest; sentrygate (OPNsense, 192.168.10.1); CT 102 ntfy; CT 103 caddy; VM 101 samba-vm
**Status:** Complete. Open loops are listed under Follow-ups.
**Tags:** monitoring, checkmk, proxmox, snmpv3, ntfy, alerting, least-privilege

---

## Why I built this

* Netdata was removed earlier today (`2026-10-12-netdata-removal.md`). That left the hypervisor and all its guests unmonitored, and a CheckMK 2.5.0p15 Community CT with **zero hosts**.
* I followed NetworkChuck's "You can monitor EVERYTHING in your homelab with this" (2026-10-12, Checkmk-sponsored) and kept its structure: agents on Linux hosts, the Proxmox API special agent with piggyback, SNMP for network gear, HTTP checks and push alerts. I deviated from it in a few places:
  * I stayed on **Community**. The video pushes the Ultimate trial, which is capped at 750 services and expires.
  * I gave the Proxmox special agent a **dedicated read-only PVE user**. The video uses an existing admin login.
  * The Proxmox host gets an **agent as well as the API**. API-only would lose the PERC/MegaRAID, IPMI and thin-pool detail, and local-lvm is already at 72%.
  * Alerts go to my own **ntfy**, not Slack.
  * The Docker part doesn't apply, because nothing here runs Docker.

## How I built it

* **Tools/stack:** CheckMK 2.5.0p15 Community (OMD site `monitoring`), check-mk-agent 2.5.0p15 (TLS registration via `cmk-agent-ctl`), Proxmox VE special agent, SNMPv3 (os-net-snmp), `check_httpv2`, ntfy 2.29.
* **Access:** all configuration went through the REST API as the automation user `automation-claude`. Its secret was typed into CT 115 by me (`/root/cmk-automation.secret`, 600) and never passed through chat. The install script's `/root/checkmk.creds` is stale, because the cmkadmin password was changed after install. I tightened it from 644 to 600.
* **Folders:** `/infra` (thearchivist, sentrygate) and `/guests` (13 CTs plus samba-vm and pbs). Guest host names match the PVE guest names, so piggyback data merges into each host automatically.
* **Proxmox host:**
  * Installed the agent `.deb` from the site; its sha256 matched the site copy (`308d850d…`). Ran an `apt-get -s` dry run first.
  * Registered it over TLS.
  * Created `checkmk@pve` with **PVEAuditor on `/`** only. Its password was generated on the host and written straight into the CheckMK password store (id `pve_checkmk`), so it never left the box.
  * Special-agent rule: port 8006, cert check off (self-signed PVE cert, LAN only).
* **Guests:** 13 CTs got the agent through `pct push` plus an install, with a dry run on all 13 first.
  * samba-vm and pbs were done through `qm guest exec`, because SSH isn't available. samba-vm rejects my key, and pbs has a host-key mismatch I didn't bypass. Each VM downloaded the `.deb` from the site, and I verified the same sha256 before installing.
  * The registration secret went over guest-agent stdin, never on a command line.
  * All 16 agents are TLS-registered in pull mode.
* **HTTP checks:** 11 `check_httpv2` rules, one per guest, each hitting `https://<svc>.home.arpa` through Caddy so the whole chain is tested. Expected codes are 200/30x/401, with response time warn/crit at 2/5 s.
  * Cert validation is **off**. `check_httpv2` uses its own built-in root list and has no custom-CA option, so trusting Caddy's root in the system store had no effect. I reverted that. Caddy's internal leaf certs last about 12 h and auto-renew, so expiry alerts would only be noise.
  * The checkmk check is pinned to `--server 192.168.10.201`, because CT 115's `/etc/hosts` maps `checkmk.home.arpa` to itself.
* **Caddy:** added a `checkmk.home.arpa` block, after taking a backup and running `caddy validate`. The Unbound host override on sentrygate was added through the GUI.
* **Sentry Gate (GUI only, per the OPNsense repo rule):**
  * Installed os-net-snmp, listening on 192.168.10.1 only, with v1/v2c off.
  * SNMPv3 user `cmkmon`, read-only, SHA-1/AES-128.
  * LAN rule allowing only 192.168.10.215 to reach the firewall on UDP 161.
  * Credentials were typed into a 600 file in CT 115, used to create the host, then `shred`ded.
* **Alerting:**
  * ntfy: added `upstream-base-url: "https://ntfy.sh"` (the iOS fix, see What broke).
  * Created a new ntfy user `checkmk` with write-only access to `homelab-alerts`. Its token is in `~monitoring/etc/ntfy-token` (600).
  * Custom notification plugin `ntfy` posts to **the ntfy CT IP, not Caddy**, so a Caddy outage can still be alerted on.
  * Rule: CRIT/UNKNOWN services, DOWN/UNREACHABLE hosts, and CRIT→OK / UNKNOWN→OK recoveries, sent to cmkadmin. `first_notification_delay` is 5 min on hosts and services.
  * Disabled the default HTML-email rule, since no user has an email address.
* **Tuning:** rules are scoped to folders or hosts, nothing global. See What broke.
* **Config/scripts:**
  * `../../configs/checkmk/ntfy-notify.py`: notification plugin
  * `../../configs/checkmk/caddy-checkmk.caddyfile`
  * `../../configs/checkmk/ntfy-server.yml.diff`
  * `../../configs/checkmk/ntfy-acl.md`
  * `../../configs/checkmk/wato-rules-export.mk.txt`: every rule, with no secrets. `hosts.mk` is deliberately not exported because it holds the SNMPv3 credentials.

## What broke

* **Issue: install-script admin credentials didn't work.**
  Symptom: REST API returned 401 using `/root/checkmk.creds`.
  Root cause: `etc/htpasswd` was modified 13 minutes after the creds file was written, because the password was changed at first login.
  Fix: a dedicated automation user, with its secret entered by hand into a file. I didn't reset the admin password.
* **Issue: SSH to the Archivist dropped mid-rollout (twice).**
  Symptom: `Timeout, server thearchivist not responding` during the CT 113 registration, then a banner-exchange timeout.
  Root cause: the Tailscale path to the home site (~77 ms) was flaky. The host itself was fine (uptime 1 day).
  Fix: `ServerAliveInterval=15` and resuming per-CT. CT 113 had completed before the drop.
* **Issue: `check_httpv2` reported `UnknownIssuer` on every Caddy site.**
  Root cause: the Rust plugin ships its own built-in root list and ignores the system CA store, so curl trusted Caddy after `update-ca-certificates` but the check didn't.
  Fix: disabled cert validation in the HTTP rules and reverted the CA install.
* **Issue: about 15 alerts on first discovery, mostly false.**
  * *Page tables CRIT on every LXC:* `/proc/meminfo` PageTables inside an LXC is host-wide (about 180 MiB), measured against the CT's 512 MiB–1 GiB. Fix: `levels_pagetables: ignore` for CTs in `/guests`.
  * *PVE CPU allocation 204%:* 49 vCPUs over 24 threads is normal LXC overcommit. Fix: levels raised to 300/400%.
  * *Snapshot age WARN at 1 day:* these are homelab-update's rolling weekly `preupdate` snapshots, so their existence is by design. Fix: warn 8 d (a missed rotation), crit 15 d.
  * *pbs "No backup found":* VM 150 is excluded from vzdump by design. Fix: that service is ignored on pbs.
  * *pbs PVE memory 101%:* the hypervisor's view counts guest page cache. Fix: no PVE-side memory levels on VMs; the in-guest Memory check is authoritative.
  * *jellyfin `motd-news` failed:* Ubuntu noise. Fix: ignored in the systemd summary.
  * *NTP Time flapping on thearchivist and pbs:* chrony's maxpoll is 1024 s (17 m 4 s), and the plugin's default `alert_delay` is `(1025, 3600)`, one second above it. Every poll cycle landed on the WARN line. Fix: `ntp_time` rule site-wide, `alert_delay` (1800, 3600).
  * *checkmk "No backup found":* the CT is new and covered by the `all 1` vzdump job. Clears after the 21:00 run.
* **Issue: samba-vm `quotaon@srv-family.service` failed at boot.**
  Symptom: `quotaon: using . on /dev/sdb1 [/srv/family]: File exists`.
  Root cause: `/srv/family` uses the ext4 `quota` feature (hidden quota inodes 3/4). Together with `usrquota,grpquota` in fstab, the kernel already enables accounting **and enforcement** at mount. The systemd generator still creates `quotaon@`, which tries to enable them a second time. Quotas were enforced all along (`quotaon -p`, and `repquota` showing the 100G limits).
  Fix: `systemctl mask quotaon@srv-family` plus `reset-failed`. The unused Aug-5 legacy files `aquota.user` and `aquota.group` were moved, not deleted, to `/root/quota-legacy-20261012/` on samba-vm, with sha256 verified before and after. Rollback is `systemctl unmask quotaon@srv-family` and moving the files back.
* **Issue: SNMPv3 "Unknown user name".**
  Root cause, in two parts:
  * The first credentials file had shifted fields (the user line wasn't `cmkmon`, and priv was empty).
  * snmpd had started at 14:39, but the user was saved to `config.xml` at 14:42 and never applied. The generated `snmpd.conf` had no `rouser` or `createUser`.
  Fix: re-entered only the two secrets (I wrote the username line myself), then pressed Apply in the GUI. After that, SHA/AES worked and every other combination was rejected.
* **Issue: iOS ntfy pushes "failing every time".**
  Root cause: `server.yml` had no `upstream-base-url`. iOS can't background-poll a self-hosted server, and ntfy's docs say delivery "can take hours" without it. The network path was fine: sentrygate advertises 192.168.10.0/24 on the tailnet, and split DNS sends `home.arpa` to .1.
  Fix: set `upstream-base-url: "https://ntfy.sh"`. Upstream receives only sha256(topic URL) and the message ID. Message bodies stay on CT 102, and the phone needs Tailscale up to fetch them.
* **Issue: my first end-to-end test never paged, and the service went stale and flapped.**
  Symptom: I injected CRIT results into `checkmk;Uptime`. Notification #0, `last_hard_state_change` equal to `last_check`, and notify.log showed only event `f` (flapping), which the rule correctly rejected.
  Root cause: agent-fed services like `Uptime` are passive and are filled in every minute by the `Check_MK` service, so `DISABLE_SVC_CHECK` on them does nothing. The real OK kept overwriting the fake CRIT. That OK↔CRIT seesaw caused the flapping, which suppresses notifications by design, and each flip restarted the 5-minute delay. It was a test-method error, not a pipeline fault.
  Fix: tested with a dedicated failing active check instead (see What worked). I put `Uptime` back to its original state: active checks disabled and flap detection on.
* **Issue: phantom "New notification" pushes with nothing in the ntfy app.**
  Symptom: empty pushes kept arriving on the iPhone at random times, while ntfy's `messages_published` counter didn't move.
  Root cause: a **relay hash collision**. The iOS upstream relay wakes the phone on ntfy.sh topic `sha256("http://ntfy.home.arpa/homelab-alerts")`. Any other self-hoster with the same base-url and topic name, both common defaults, shares that channel. Their publishes woke my phone, the app asked my server for an unknown message ID, and it showed an empty placeholder.
  Confirmation: I listened read-only to both relay channels on ntfy.sh. A `poll_request` arrived at 18:06:12 while my server's counter stayed at 12 before and after, and CheckMK sent nothing. Public `ntfy.sh/homelab-alerts` returns 403, meaning someone has reserved that name.
  Fix: renamed both topics to `homelab-{alerts,updates}-<10 random chars>`, made up of letters and digits only. Three publishers were switched:
  * the CheckMK plugin, which now reads its URL from `~monitoring/etc/ntfy-url` (600) so the name is never in code;
  * `/usr/local/sbin/homelab-update`;
  * `/etc/thinpool-alert.conf`.

  Each got a `.bak-20261012` copy, a temp file, and an `mv`. New ACLs were added before the switch, and the old ones are removed only after the phone is moved over. The repo copies use `<SET-ON-HOST>`, because a known topic name is enough to send phone wake-ups. Message content never leaked in either direction: it only ever lives on the origin server.
* **Issue: nothing on the phone even from a direct ntfy POST.**
  Root cause: ntfy stats showed `subscribers=0`. `homelab-alerts` was a brand-new topic that the phone had never subscribed to.
  Fix: subscribed in the iOS app to `homelab-alerts` on `http://ntfy.home.arpa` (it must match `base-url` exactly, because the upstream relay keys on a hash of it) as `tobias`.

## What worked

* 17 hosts are monitored: thearchivist, 13 CTs, samba-vm, pbs and sentrygate. All are UP.
* Host coverage includes MegaRAID physical/logical disks and BBU, IPMI, LVM-thin and directory storages, chrony, and PVE node info. Every guest also gets PVE backup-status and snapshot-age services.
* All 11 web UIs return 200 through Caddy.
* After tuning, the only problems left were the expected ones: checkmk's first backup is pending, and the samba quota alert cleared once its unit was masked.
* **End-to-end alerting verified on the phone.** I added a temporary `check_httpv2` rule against a closed port (`192.168.10.215:9`): a real active check that fails consistently and touches no service. It went CRIT at 16:00:43. At 16:03:47 `notify.log` showed the ntfy rule `-> matches!`, `executing .../notifications/ntfy`, `Output: ntfy: HTTP 200`, and the push arrived on the iPhone after subscribing. Pointing the check at a working URL produced a **recovery** push (HTTP 200). The test rule was then deleted, and 0 test services remain.
  * It paged about 3 minutes after the failure started, not the configured 5. The likely reason is that the test service had never been OK, so the delay was counted from earlier. Real services going from OK to CRIT should wait the full 5 minutes, but that's unverified. Watch the timing of the first real alert.

## What I'd do differently

* Apply OPNsense plugin settings in the same sitting as creating users. A saved-but-not-applied user cost a debugging round.
* Don't trust install-script credential files as a source of truth once a human has logged in.

## Follow-ups

* After samba-vm's next reboot, `quotaon -p /srv/family` must still say user and group quotas `is on`.
* checkmk `Proxmox VE VM Backup Status` should be OK after 2026-10-12 21:00.
* Check that `homelab-updates` on the phone uses exactly `http://ntfy.home.arpa`. The upstream fix should also resolve its missed pushes.
* `netdata.home.arpa` host override on sentrygate is still pointing at Caddy and can be deleted (carried over from the netdata writeup).
* pbs SSH host-key mismatch is unexplained. Investigate before trusting SSH to 192.168.10.220.
* Remove `automation-claude` once configuration is finished, or keep it as an API account and rotate its secret.

---

## Resume-ready summary

* Deployed CheckMK monitoring across a Proxmox homelab: 17 hosts and about 400 services, with TLS-registered agents, a least-privilege (PVEAuditor) Proxmox API integration with piggybacked guest data, SNMPv3 on an OPNsense firewall, and end-to-end HTTPS checks through a reverse proxy. Tuned out roughly 15 false positives with scoped, documented rules (LXC page-table artifacts, overcommit, snapshot rotation).
* Diagnosed a long-standing iOS push failure to a missing ntfy upstream relay and built a dependency-aware alert path (ntfy plugin bypassing the proxy it monitors, 5-minute persistence delay). Along the way I found and fixed a masked-cause quota service failure on a family file server without touching enforcement.
