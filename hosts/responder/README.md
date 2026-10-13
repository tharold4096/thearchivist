# Responder (CT 116)

When Checkmk raises a **major** alert (CRIT, UNKNOWN, host DOWN/UNREACHABLE), the responder runs a
read-only diagnosis with headless Claude Code and proposes at most one allowlisted fix. Tobias
approves or denies the proposal from an ntfy push on his iPhone. Deterministic code, not Claude,
executes the action, verifies it, and reports back. Once an exact action has been approved, it is
remembered and runs without a tap next time, except on protected targets.

```
Checkmk (CT 115) ──responder plugin──▶ POST /alert  (source IP + bearer)
                  └─ntfy plugin──────▶ phone        (plain alert, independent fallback)

/alert ─▶ store: dedupe into one job per host+service ─▶ new job?
            └▶ run-claude (as rclaude): cmk-read / gate-read only, JSON verdict
                 └▶ validate against registry.toml ─▶ no proposal: diagnosis push
                                                   └▶ proposal:
                       remembered (grants) and within limits? ─▶ executor runs it, push + [Revoke]
                       otherwise ─▶ push [Approve] [Deny] ─▶ first tap claims the job atomically
                                                             ─▶ executor ─▶ verify ─▶ push result
every outcome ─▶ journal.py ─▶ journal/responder/ in this repo (scrubbed summary)
```

## Trust boundary

The responder ingests attacker-influenceable text (service output, logs), so nothing it decides is
trusted. Enforcement lives elsewhere:

| Control | Where | What it stops |
|---|---|---|
| `rgate` forced command, `restrict`, `from=` | each target (`deploy/rgate`) | any command except fixed verbs, from anywhere but CT 116 |
| Claude's key pinned to `rgate read` | target `authorized_keys` | Claude causing a write, even with the wrapper bypassed |
| `rclaude` Unix user | CT 116 | Claude reading the job DB, grants, executor key, or service secrets |
| `--tools Bash`, allow only `gate-read`/`cmk-read`, `dontAsk` | `bin/run-claude` (root-owned) | any other command or tool (tested: `cat /etc/hostname` denied) |
| registry validation | `registry.py`, `diagnose.py` | proposals for unregistered hosts or verbs, or for a different host than the one alerting |
| single-use hashed tokens, atomic claim | `store.py` | replays, double taps, approve-after-deny, approve-after-expiry |
| `start_execution` guard | `store.py` | a second execution of the same job |
| protected list | `registry.toml`, `grants.py` | remembering actions on security services or Vaultwarden |
| nftables on :8787 | `deploy/nftables.conf` | anything but Sentry (tailnet) and Checkmk reaching the service |

## Files

| File | Role |
|---|---|
| `app.py` | HTTP service: intake, taps, revoke, sweeper |
| `store.py` | job state machine (SQLite); every transition is a guarded UPDATE |
| `grants.py` | learned approvals, auto-run limits (2 per action per 24h, 4 per hour overall), revoke |
| `registry.toml` / `registry.py` | the allowlist: hosts, verbs, verification, protected targets |
| `diagnose.py` | builds the prompt (alert wrapped as untrusted), runs Claude, validates the verdict |
| `executor.py` | runs the verb with the executor key, verifies (systemd plus the health URL) |
| `journal.py` | publishes scrubbed incident records to this repo |
| `notify.py` | ntfy publishing |
| `bin/run-claude` | fixed Claude invocation as `rclaude` |
| `bin/gate-read`, `bin/cmk-read` | Claude's only tools |
| `system-prompt.md`, `diagnosis.schema.json` | Claude's instructions and the required output shape |
| `deploy/` | systemd unit, sudoers, nftables, the `rgate` gate for targets |
| `tests/` | `python3 -m unittest discover -s tests` (store races, guards, grants) |

## Adding a host or verb

1. On the target: create the `rgate` user, install `deploy/rgate` (set its unit), add one exact sudoers
   line per write verb, and add both keys to `authorized_keys` with `restrict,from="192.168.10.216"`.
   The executor key gets `command="/usr/local/bin/rgate"` and the Claude key gets
   `command="/usr/local/bin/rgate read"`.
2. Pin the target's host key, read out-of-band through `pct`, in `/etc/responder/known_hosts` and in
   `~responder/.ssh/known_hosts`.
3. Run the boundary tests from CT 116: injection-shaped requests, a write verb with the Claude key,
   and the key used from another host. All must be refused and appear in `journalctl -t rgate`.
4. Add the entry to `registry.toml`, including `verify_url`/`verify_expect`, and set `protected` if it
   applies. Then `systemctl restart responder`.

## Rebuild checklist (everything that is not in git)

| Item | Location | Notes |
|---|---|---|
| Claude OAuth token | CT 116 `/etc/responder/claude.env` | `root:rclaude 640` |
| Service env: ntfy URL and token, alert bearer | CT 116 `/etc/responder/responder.env` | `root:responder 640` |
| Checkmk read-only secret | CT 116 `/etc/responder/cmk-ro.secret` | `root:rclaude 640`; user `responder-ro`, guest role |
| Executor key | CT 116 `~responder/.ssh/gate_ed25519` | full rgate mode on targets |
| Claude key | CT 116 `/var/lib/rclaude/.ssh/read_ed25519` | `rgate read` on targets |
| Journal deploy key | CT 116 `~responder/.ssh/journal_ed25519` | GitHub deploy key with write access, this repo only |
| Pinned host keys | `/etc/responder/known_hosts`, `known_hosts_github` | GitHub's key verified against `gh api meta` |
| Job DB, transcripts | CT 116 `/var/lib/responder/` | state; safe to lose (jobs reopen on the next alert) |
| sudoers | CT 116 `/etc/sudoers.d/responder` | `deploy/sudoers-responder` |
| Alert bearer (Checkmk side) | CT 115 `~monitoring/etc/responder.secret` | must match `ALERT_TOKEN` |
| ntfy user `responder` | CT 102 | write-only on the alerts topic |
| Checkmk notification rule | CT 115 | cloned from the ntfy rule, plugin `responder` |
| OPNsense rule | Sentry, Tailscale interface | iPhone to `192.168.10.216:8787` TCP |
| `rgate`, sudoers, `authorized_keys` | each target (CT 100 so far) | see "Adding a host" |

## Known limits

* The host is powered off 23:00 to 07:45, so there are no alerts or approvals overnight. Approval links
  expire after 30 minutes.
* iOS keeps buttons tappable after a decision (`clear=true`, updates and deletes don't work). The
  server-side claim makes repeat taps harmless.
* All tailnet traffic arrives from `192.168.10.1` (Sentry SNAT), so the approval token, not the
  source IP, authenticates a tap.
