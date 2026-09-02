# Wazuh Agent Deployment — Sentry Gate & The Archivist

**Date:** 2026-09-02
**Machine(s):** Sentry Gate (OPNsense 26.7.3_8 / FreeBSD 15.1) · The Archivist (Proxmox VE 9.2.11) · Wazuh manager (LXC 104)
**Status:** Complete — with two verifications deliberately left open (see [Open loops](#open-loops))
**Tags:** SIEM, Wazuh, OPNsense, Proxmox, logging, hardening, FIM

---

## Why I built this

The lab had a Wazuh manager with zero agents enrolled — a SIEM watching nothing.
The goal was to get the two machines that matter most reporting into it: the
firewall that sees all north–south traffic, and the hypervisor that hosts
everything else.

Two constraints shaped every decision:

- **The manager is offline ~9 hours a night.** The Archivist powers down at
  23:00 and wakes at 07:45 via IPMI. Anything an agent produces in that window
  must survive in a local buffer or it is lost silently.
- **Sentry Gate is a Dell Inspiron 530**: Core 2, 2.95 GB RAM, and — as this
  work discovered — **no swap at all**. Every megabyte of agent buffer competes
  with Unbound holding a 333,925-entry DNSBL.

---

## Part 1 — The plugin migration failure

### Symptom

Installing `os-wazuh-agent 1.3_1` emitted two errors:

```
Failed OPNsense\WazuhAgent\WazuhAgent from 0.0.0 to 1.0.3
Reloading template OPNsense/WazuhAgent: ERR
```

Saving settings and hitting Apply in the GUI appeared to fix things — the agent
came up and connected. But it was unclear whether the plugin was actually
healthy or half-initialised.

### Initial diagnosis (wrong turn worth recording)

The first `grep '<WazuhAgent>' /conf/config.xml` returned nothing, which looked
like the migration had never created the config node at all. **That was a false
negative** — the tag carries attributes, so it is
`<WazuhAgent version="..." persisted_at="..." description="...">` and an exact
match on `<WazuhAgent>` cannot hit it. Always grep for the bare tag name.

The node existed and held correct settings. The real tell was its version stamp:

```
<WazuhAgent version="0.0.0" ...>          <-- stuck
```

Every other model in `config.xml` carries a real version (`unboundplus 1.0.15`,
`Nut 1.0.4`), and the model itself declares `<version>1.0.3</version>`.

### Root cause

The plugin ships **no `Migrations/` directory at all** — so no migration *code*
failed. What failed was the save that follows it:

```xml
<!-- mvc/app/models/OPNsense/WazuhAgent/WazuhAgent.xml -->
<server_address type="HostnameField">
    <Required>Y</Required>        <!-- and no <Default> -->
```

At `pkg install` time there was no `<WazuhAgent>` node yet. The migration runner
instantiated the model, got an empty `server_address`, hit `Required=Y` with no
default, and the save threw. The version stamp is written *after* that save, so
it stayed `0.0.0`.

`Reloading template ... ERR` is the **same root cause one step downstream**:
with no config node, the template's `OPNsense.WazuhAgent.general.*` lookups had
nothing to dereference.

This is a plugin packaging bug — a `Required` field with no `Default`, evaluated
on a fresh install.

### Fix

The GUI Save supplied `server_address`, which silently fixed both symptoms. Only
the stale stamp remained. Correct it with the supported migration runner:

```sh
# On Sentry Gate
cp -p /conf/config.xml /conf/config.xml.bak-premigrate-$(date +%Y%m%d-%H%M%S)
/usr/local/sbin/pluginctl -v          # validate models first (read-only)
/usr/local/sbin/pluginctl -m          # run migrations
```

Expected output — this is the exact operation that failed at install:

```
Migrated OPNsense\WazuhAgent\WazuhAgent from 0.0.0 to 1.0.3
```

Then confirm the second symptom is gone:

```sh
configctl template reload OPNsense/WazuhAgent     # expect: OK
```

**Why this is proof and not a guess:** the only thing that changed between the
install-time failure and the successful re-run is that `server_address` is now
populated. Nothing else was touched.

### Leaving it unfixed

Not fatal. Every future `pkg upgrade` of the plugin re-runs migration from
`0.0.0` and will now succeed, so it self-heals. But until it does, the install
log keeps throwing that error and you cannot distinguish a real failure from
this stale one.

---

## Part 2 — Things that bit us, worth knowing before you start

### `configctl` namespace is `wazuh_agent`, with an underscore

```sh
configctl wazuh_agent status      # works
configctl wazuhagent status       # "Action not allowed or missing"
```

The *model* mount is `//OPNsense/WazuhAgent` and the API endpoint is
`/api/wazuhagent/settings/set` (no underscore). The two genuinely differ — do
not infer one from the other. The configd action file is
`/usr/local/opnsense/service/conf/actions.d/actions_wazuh_agent.conf`.

Note `wazuh_agent start|restart` also restarts syslog-ng, because the agent
reads `/var/ossec/logs/opnsense_syslog.log`, which syslog-ng writes.

### `authd.pass` is deleted on every restart unless config.xml holds it

This one cost real time. `/etc/rc.conf.d/wazuh_agent` (a template target)
declares:

```sh
wazuh_agent_setup="/usr/local/opnsense/scripts/wazuh/setup.php"
```

FreeBSD's `rc.subr` runs `${name}_setup` on **every start and restart**, and
that script is unambiguous:

```php
if (!empty((string)$mdl->auth->password)) {
    // write auth->password into /var/ossec/etc/authd.pass, 0640 root:wazuh
} elseif (file_exists($authd_pass)) {
    unlink($authd_pass);          // <-- deletes a hand-placed file
}
```

**`config.xml` is the single source of truth for `authd.pass` on OPNsense.** A
password placed by hand is destroyed the next time the service restarts.

Isolated by testing each half of the configd action:

| Command | `authd.pass` afterwards |
|---|---|
| `pluginctl -s syslog-ng restart` | present |
| `/var/ossec/bin/wazuh-control restart` | present |
| **`/usr/local/etc/rc.d/wazuh-agent onerestart`** | **deleted** |

There is an ordering trap: `setup.php` runs *before* the agent starts, so a
manually-placed file is removed before the agent could ever read it.

**Decision taken here:** put the password in the GUI field
(*Services → Wazuh Agent → Settings → Auth → Password*). It then persists
correctly. The cost is that the enrollment password lives in `/conf/config.xml`
and therefore inside every config backup/export — which is exactly why this repo's
`.gitignore` blocks `*.xml`. **Never commit a config export.**

### The stock pfSense rule silently discards firewall block alerts

Decoding is fine. `wazuh-logtest` on a real OPNsense filterlog line:

```
Phase 2: name: 'pf'   action: 'block'
         srcip: '192.168.1.206'   dstip: '192.168.1.255'
         srcport: '39867'  dstport: '20002'  protocol: 'udp'
Phase 3: id: '87701'  level: '5'  "pfSense firewall drop event."
```

**No custom decoder is needed** — the concern that OPNsense field ordering has
diverged from pfSense did not hold on 4.14.7. But the stock rule carries:

```xml
<rule id="87701" level="5">
  <options>no_log</options>      <!-- "they go to their own log file" -->
```

That intent is not met. `firewall.log` is only written for rules in the
`firewall` group, and 87701 is in `firewall_block`. **So the alert is suppressed
and written nowhere.**

This is nastier than an unparsed string, because every health signal looks
correct while nothing arrives:

```
events_processed   climbing
events_dropped     0
decoder            pf, all fields extracted
alerts_written     2        <-- flat
firewall_written   0        <-- flat
```

Fix is a **child rule**, not an overwrite — `no_log` suppresses only the rule
that declares it, and a child rule is not reverted by a ruleset upgrade. See
`configs/wazuh-manager/local_rules.xml` (rules `100110`–`100116`).

---

## Part 3 — Volume control

### Audit what is actually logging

```sh
# On Sentry Gate — rank rules by real log volume
LOG=/var/log/filter/filter_$(date +%Y%m%d).log
sed 's/.*\] //' $LOG | awk -F, '{print $4, $5, $7, $8}' | sort | uniq -c | sort -rn | head
```

On 2026-09-02 this showed one rule producing **153,957 of 223,627 lines (69%)**:
`9e635b80…` = *"Allow exit node routing over tailscale"* (pass, log ON). Logging
every packet of exit-node traffic tells you nothing a pass rule did not already
authorise. Disabling logging on that one rule is the single highest-value change.

**Read the hourly breakdown before trusting a daily total**, though — this is a
correction to my own first analysis:

```sh
grep -oE "$(date +%Y-%m-%d)T[0-9]{2}" $LOG | uniq -c
```

That rule's 153,957 lines were **149,371 in a single hour**. Its steady-state
contribution is only ~20/min. So disabling it does *not* cut the overnight rate
by 69% — what it removes is the **burst risk**, which is the thing that actually
overflows a buffer.

### Real overnight numbers

Measured from hourly totals across the 23:00→07:45 window:

| | |
|---|---|
| Overnight filterlog events | **~37,650** |
| Plus unbound/audit (~2%) | **~38,400** |
| Effective rate | ~1.2 events/sec |
| `queue_size` 5000 (default) | covers ~1.2 h of 9 — **most of every night lost** |
| `queue_size` 50000 | covers the full window, ~30% headroom |

A single anomalous hour produced 159,191 lines — **any burst like that overflows
50,000 regardless**. Buffer sizing does not solve bursts; source-side volume
control does.

### Raise the buffer

The plugin's `ossec.conf` template hardcodes `queue_size 5000`, then globs
`ossec_config.d/*.conf`. A fragment therefore emits a **second**
`<client_buffer>` block — and the later block wins. Do not hand-edit
`ossec.conf`; it is regenerated on every apply.

Deploy `configs/sentrygate/ossec_config.d/010-client-buffer.conf`, then:

```sh
configctl template reload OPNsense/WazuhAgent
configctl wazuh_agent restart
```

**Verify the effective value rather than assuming the override won.** The agent
only logs its buffer size when the manager pushes shared config, so force one:

```sh
# In the Wazuh LXC — touch the shared config to trigger a push
pct exec 104 -- sh -c 'touch /var/ossec/etc/shared/default/agent.conf; systemctl restart wazuh-manager'
```

```sh
# On Sentry Gate — expect size: 50000
grep "Buffer agent.conf updated" /var/ossec/logs/ossec.log | tail -1
```

RAM cost is ~203 bytes/event × 50,000 ≈ **10 MB**.

### Swap (Sentry Gate had none)

`swapinfo` returned an empty table on a 2.95 GB box, so memory pressure was a
hard kill rather than a slowdown. The root device is a **PNY CS900 250 GB SSD**,
not the CF card that OPNsense Nano images assume — so the usual no-swap-on-flash
rationale does not apply.

```sh
# On Sentry Gate
dd if=/dev/zero of=/usr/swap0 bs=1m count=2048
chmod 0600 /usr/swap0
printf 'md99\tnone\t\t\tswap\tsw,file=/usr/swap0,late\t0\t0\n' >> /etc/fstab
swapon -aL
swapinfo -h        # expect /dev/md99  2.0G
```

---

## Part 4 — Unbound DNSBL blocks (requires a bridge)

**There is no path in OPNsense that sends DNSBL blocks to syslog.** On a block,
`dnsbl_module` calls `Logger.log_entry()`, which writes a pipe-delimited record
to the FIFO `/var/unbound/data/dns_logger`. Its only stock consumer is
`scripts/unbound/logger.py`, which writes to **SQLite** for the Reporting UI.
With nothing attached, unbound logs this every 10 s and the events are dropped:

```
dnsbl_module: attempting to open pipe
dnsbl_module: no logging backend found.
```

The bridge (`configs/sentrygate/unbound-dnsbl-wazuh.py`) attaches to that FIFO,
keeps only genuine blocks, and emits JSON lines. Using `log_format json` means
Wazuh's **built-in JSON decoder** extracts every field — no custom decoder at all.

FIFO wire format (13 pipe-separated fields):

```
uuid|created_at|client|family|type|domain|action|source|blocklist|rcode|resolve_time_ms|dnssec_status|ttl
```

`uuid` is the policy id and is non-empty **only for blocks** — unblocked queries
traverse the same FIFO. Filtering on it keeps volume proportional to enforcement
rather than to total DNS traffic.

### Two traps

**A FIFO feeds exactly one reader.** If you enable Unbound *Reporting* in the
GUI, `logger.py` and this bridge will split the stream and both datasets go
silently incomplete. The daemon refuses to start if `logger.py` is running.

> Corollary learned the hard way: **never run `grep -r` under `/var/unbound`.**
> A recursive grep will block on the FIFO and consume the DNSBL stream. One did,
> and reached 205 MB RSS before it was noticed — dangerous on a swapless 3 GB box.

**SIGTERM must raise, not set a flag.** The daemon blocks in `open()`/`read()`
on the FIFO. Under PEP 475 a handler that only sets a flag lets Python retry the
interrupted syscall, so the process ignores SIGTERM until the next block arrives
— possibly hours. `service ... stop` reports success, the old process survives,
and a subsequent start leaves **two readers splitting the FIFO**. Also do not
pass `daemon -r`: it respawns the child that `stop` just killed.

### Policy scope

The DNSBL policy is scoped by `source_nets`. Querying from an out-of-scope source
(including the firewall's own `127.0.0.1`) returns normal answers and looks like
filtering is broken. Test from an in-scope address:

```sh
dig +short instagram.com @100.116.54.77      # expect 0.0.0.0 from an in-policy client
dig +short wikipedia.org @100.116.54.77      # control: normal answer
```

---

## Part 5 — Adding a new agent

### Common to every platform

1. **Version-match the manager first.** An agent newer than its manager is
   unsupported.
   ```sh
   pct exec 104 -- /var/ossec/bin/wazuh-control info    # WAZUH_VERSION="v4.14.7"
   ```
2. **Enrollment needs the password** — port 1515 requires it since this work.
   ```sh
   pct exec 104 -- cat /var/ossec/etc/authd.pass
   ```
   Move it **host-local or host-to-host — never via your laptop.** If the target
   host can read the source itself, that is the only acceptable method:
   ```sh
   # On the Archivist, whose LXC 104 IS the manager
   pct exec 104 -- cat /var/ossec/etc/authd.pass > /var/ossec/etc/authd.pass
   chown root:wazuh /var/ossec/etc/authd.pass && chmod 640 /var/ossec/etc/authd.pass
   ```
3. **Verify by hash, never by printing the secret.**
   ```sh
   sha256sum /var/ossec/etc/authd.pass
   pct exec 104 -- sha256sum /var/ossec/etc/authd.pass
   ```
4. **Confirm Active on the manager**, not just "the service is running":
   ```sh
   pct exec 104 -- /var/ossec/bin/agent_control -l
   ```

### Debian / Ubuntu VM  *(verified on Debian 13, The Archivist)*

```bash
curl -sS https://packages.wazuh.com/key/GPG-KEY-WAZUH \
  | gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
chmod 644 /usr/share/keyrings/wazuh.gpg
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
  > /etc/apt/sources.list.d/wazuh.list
apt-get update

# Pin the version to the manager's. Do not take "latest".
WAZUH_MANAGER="192.168.10.204" WAZUH_AGENT_NAME="<hostname>" \
  apt-get install -y wazuh-agent=4.14.7-1

apt-mark hold wazuh-agent        # see "Update orchestrator" below
systemctl daemon-reload && systemctl enable --now wazuh-agent
```

Expected in `/var/ossec/logs/ossec.log`:

```
Using password specified on file: etc/authd.pass
Valid key received
Connected to the server ([192.168.10.204]:1514/tcp).
```

**Debian 13 has no `/var/log/auth.log`** — it is journald-only with no rsyslog.
Do not add a localfile for it. The agent's **default journald localfile already
carries sshd and sudo**; that is where SSH/sudo auth comes from.

### Unprivileged LXC  *(constraints verified on CTID 104)*

Install exactly as Debian above. What differs is what will not work.

**Works:** FIM (syscheck), log collection, journald, SCA, syscollector,
active-response that only writes files.

**Does not work, and why:**

- **`/proc/sys` is mounted read-only.** Confirmed:
  `proc on /proc/sys type proc (ro,relatime)`. Anything writing a sysctl fails.
  (`/proc/sys/net` is mounted separately and *is* writable.)
- **Kernel auditing is unavailable.** The audit subsystem is not namespaced, so
  audit netlink cannot be used from a container regardless of capabilities. No
  `auditd`, no `who-data` FIM — use plain `realtime` instead.
- **Capabilities are misleading.** `CapEff` shows `cap_sys_admin`,
  `cap_ipc_lock`, `cap_audit_control` and friends, and `capsh --decode` will
  happily list them. In an unprivileged container these are **namespaced** — they
  confer no host privilege. Do not conclude a feature will work because the
  capability appears present.
- **Rootcheck runs but is worthless.** It produced **104 alerts, every one of
  them `File present on /dev.`** — normal container device nodes flagged as
  anomalies. Disable it:
  ```xml
  <rootcheck><disabled>yes</disabled></rootcheck>
  ```

### Windows 11 — Tower, dorm, over Tailscale  *(NOT yet verified)*

> Everything in this section is written from configuration facts, not from a
> completed install. Tower has been offline (last seen 23h ago) throughout.

**Do the Tailscale ACL first — enrollment fails silently without it.** Tower's
ACL is currently narrowed to `10.10.10.0/24` only. It needs an explicit grant to
the manager:

```jsonc
// Tailscale ACL — Tower must reach the manager on both ports
{
  "action": "accept",
  "src":    ["towerofpower"],
  "dst":    ["192.168.10.204:1514", "192.168.10.204:1515"]
}
```

Sentry Gate advertises `192.168.10.0/24` as a subnet router, so the route
exists — the ACL is the only thing in the way. **Tailnet identity here is
GitHub-based (`tharold4096@github`), not email.** Using the email form in an ACL
will not match.

```powershell
# Install (run as Administrator). Version must match the manager.
msiexec /i wazuh-agent-4.14.7-1.msi /q ^
  WAZUH_MANAGER="192.168.10.204" ^
  WAZUH_REGISTRATION_PASSWORD="<from authd.pass>" ^
  WAZUH_AGENT_NAME="towerofpower"

NET START Wazuh
```

Verify the path *before* blaming the agent:

```powershell
Test-NetConnection 192.168.10.204 -Port 1515
Test-NetConnection 192.168.10.204 -Port 1514
```

Expect the agent to go stale nightly during the 23:00–07:45 window — that is the
manager being down, not a Tower fault.

### Arch — Omarchy  *(NOT yet verified)*

No official Arch package. Either build `wazuh-agent` from the AUR, or unpack the
generic tarball. Version-pin to the manager either way, then configure
`/var/ossec/etc/ossec.conf` with `<address>192.168.10.204</address>` and place
`authd.pass` as above. This laptop is `100.113.94.88` and is **inside the DNSBL
policy's `source_nets`**, so it is a convenient place to generate test blocks.

---

## Part 6 — Update orchestrator reconciliation

`/usr/local/sbin/homelab-update` runs `apt-get dist-upgrade` on the Proxmox host
every Sunday 08:15. Wazuh upgrades are order-sensitive (**indexer → server →
dashboard**) and an agent must never be newer than its manager, so an unattended
run could break the agent silently.

**Applied:** `apt-mark hold wazuh-agent`, plus a `WAZUH_HELD_PACKAGES` block and
a `report_holds()` function in the orchestrator. Every weekly report now prints:

```
## Package holds
- apt holds on host: wazuh-agent
```

and a missing hold raises a **failure**, which triggers the high-priority ntfy
push. The pin is visible where you would actually look instead of being a silent
surprise.

To upgrade deliberately: upgrade the manager stack in LXC 104 first, then
`apt-mark unhold` → `apt-get install wazuh-agent=<version>` → `apt-mark hold`.

> ⚠ **Two pre-existing issues found while reading this script — not fixed here.**
> 1. `LXC_IDS=(0 0 0)` is still the `<-- SET ME` placeholder, so **no containers
>    are patched at all**, including LXC 104. The Wazuh manager stack is not
>    being updated. (This accidentally protects the indexer→server→dashboard
>    ordering, but leaves the stack unpatched.)
> 2. The script contains a **live ntfy bearer token**. Never commit this file to
>    the repo as-is.

---

## Rebuild checklist — files that live OUTSIDE config.xml

An OPNsense config restore onto fresh media brings back `config.xml` **and
nothing else**. Everything below must be replaced by hand. All are mirrored in
`configs/sentrygate/` in this repo except the two secrets.

| File | Purpose | In repo? |
|---|---|---|
| `ossec_config.d/010-client-buffer.conf` | `queue_size` 50000 override | ✅ |
| `ossec_config.d/020-localfile-dnsbl.conf` | ingest DNSBL blocks | ✅ |
| `/usr/local/sbin/unbound-dnsbl-wazuh` | FIFO → JSON bridge daemon (0555) | ✅ |
| `/usr/local/etc/rc.d/unbound_dnsbl_wazuh` | rc script for the bridge (0555) | ✅ |
| `/etc/newsyslog.conf.d/unbound-dnsbl.conf` | rotate `blocks.log` | ✅ |
| `/etc/rc.conf` → `unbound_dnsbl_wazuh_enable="YES"` | enable bridge at boot | ✅ (documented) |
| `/etc/fstab` → `md99 ... file=/usr/swap0,late` | swap entry | ✅ (documented) |
| `/usr/swap0` | 2 GB swap file — recreate with `dd` | n/a |
| `/var/ossec/etc/client.keys` | agent identity — **or** re-enroll | ❌ secret |
| `/var/ossec/etc/authd.pass` | regenerated from config.xml by `setup.php` | ❌ secret |
| `actions_wakearchivist.conf` | pre-existing (IPMI wake) | tracked separately |
| `/conf/ipmi-archivist.pw` | pre-existing | ❌ secret |

Directories to recreate: `/var/log/unbound-dnsbl/`.

> **Note:** `actions_wakearchivist.conf` and `/conf/ipmi-archivist.pw` were **not
> found on Sentry Gate** during this work. Either they live at different paths
> than recorded, or they were already lost in an earlier rebuild. Worth checking.

On the manager (LXC 104), outside any Proxmox backup of `/etc`:

| File | Purpose | In repo? |
|---|---|---|
| `/var/ossec/etc/rules/local_rules.xml` | DNSBL + firewall-block rules | ✅ |
| `/var/ossec/etc/ossec.conf` → `<use_password>yes</use_password>` | enrollment auth | ✅ (documented) |
| `/var/ossec/etc/authd.pass` | shared enrollment secret | ❌ secret |

---

## What worked — evidence

- **Agents Active:** `001 sentrygate.home.internal` and `002 thearchivist`, both
  `Active` on the manager, single instance each, verified with `sockstat`/`ps`
  rather than rc wrapper output.
- **Enrollment is authenticated.** Live negative test from Sentry Gate:
  `agent-auth` with no password → `ERROR: Invalid password. Unable to add agent`.
  Positive test: the Archivist enrolled with
  `Using password specified on file: etc/authd.pass`.
- **Buffer confirmed at the agent**, not just in config:
  `Buffer agent.conf updated, enable: 1 size: 50000`.
- **Firewall block, end to end in 9 seconds** — deliberate `nc` to port 853 at
  13:10:22, alert at 13:10:31, with parsed fields:
  ```
  rule=100112 lvl=5  OPNsense firewall BLOCK: 100.113.94.88:48980 -> 100.116.54.77:853 tcp
     srcip=100.113.94.88  dstip=100.116.54.77  dstport=853  proto=tcp  action=block
  ```
- **DNSBL block, end to end in ~2 seconds** — query at 12:58:59, alert at
  12:59:01:
  ```
  rule=100101 lvl=5  Unbound DNSBL: blocked youtube.com for client 100.113.94.88 [list: Custom]
     srcip=100.113.94.88  domain=youtube.com  blocklist=Custom
  ```
- **`alerts_written` went 2 → 21** the moment the `no_log` override landed.
- **Archivist monitoring live:** `sshd: authentication success` with srcip and
  user; FIM on `/etc/ssh` detected a test file `added` in 3 s and `deleted` in
  under a minute, `mode=realtime`.
- **Swap active:** `/dev/md99 2.0G` — added when free RAM had fallen to 95 MB.

---

## Open loops

Reported honestly rather than declared done:

1. **Overnight buffer gap is projected, not measured.** The 9-hour window has not
   yet been observed. After the next power cycle (~07:45), check for gaps:
   ```sh
   grep -iE "Unable to connect|Connected to the server|queue" /var/ossec/logs/ossec.log | tail -20
   ```
   and compare the event count either side of the outage against ~38,400.
2. **Swap reboot-survival is unverified.** The `fstab` entry is correct and swap
   is live, but no reboot has happened. After the next one: `swapinfo -h`.
3. ~~`authd.pass` on Sentry Gate depends on the GUI password field.~~
   **CLOSED 2026-09-02 13:30.** Password set in the GUI; `authd.pass` is written
   by `setup.php` with a hash matching the manager's copy, and — the point of the
   exercise — it now **survives `configctl wazuh_agent restart`**, which
   previously deleted it. Agent stayed Active, single instance.
4. **Windows (Tower) and Arch (Omarchy) agents are documented but not installed.**
   Tower has been offline throughout; the Tailscale ACL grant is untested.
5. **`homelab-update` still has `LXC_IDS=(0 0 0)`** — no container is being
   patched.

---

## What I'd do differently

- **Grep for the bare tag name, not `<Tag>`.** One false negative on
  `<WazuhAgent>` sent the whole first diagnosis down the wrong path.
- **Search the whole plugin tree before declaring a field unused.** Claiming
  `auth.password` was dead code was wrong — the consumer was in `scripts/wazuh/`,
  outside the templates directory I searched.
- **Never nest quoting through `pct exec`.** A mangled `grep` produced "0 block
  events reaching the manager" when 46 were arriving. Push a script in via
  base64 and run it there.
- **Read hourly, not daily, before sizing anything.** A 69%-of-daily-volume rule
  turned out to be one anomalous hour.

---

## Resume-ready summary

Deployed and hardened a Wazuh SIEM agent fleet across a heterogeneous homelab
(FreeBSD/OPNsense firewall, Proxmox hypervisor, unprivileged LXC), diagnosing a
failed plugin migration to a `Required`-field-without-default packaging bug and
restoring it via OPNsense's model-migration runner. Closed an unauthenticated
agent-enrollment path (port 1515) with a generated credential, verified by a live
negative test. Identified through empirical log analysis that a single firewall
rule produced 69% of 223,000 daily log events, and that Wazuh's stock pfSense
ruleset silently discarded every firewall-block alert via an ineffective
`no_log` option — diagnosed against `alerts_written`/`firewall_written` counters
and fixed with upgrade-safe child rules, raising alert throughput from 2 to 21
immediately. Built a Python bridge daemon exposing Unbound DNSBL enforcement
events — previously written only to a FIFO consumed by a SQLite reporting
backend — as JSON for native decoding, making DNS-layer content filtering
searchable and correlatable for the first time. Sized agent buffering against a
measured ~38,400-event nightly manager outage and added swap to a swapless
3 GB firewall.
