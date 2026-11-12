#!/usr/bin/env bash
# Did the Sure VM (106 "budget") survive the last nightly power cycle
# (host cron 22:55 -> shutdown 23:00, RTC wake 07:45)?
# Read-only. Run from Omarchy the morning after:  bash sure-powercycle-check.sh
# Needs: root SSH to thearchivist, tobias SSH to budget, jq.
set -u
PVE=root@192.168.10.202
VM=tobias@192.168.10.206
VMID=106
URL=https://budget.home.arpa/
rc=0
ok()  { printf 'PASS  %s\n' "$*"; }
bad() { printf 'FAIL  %s\n' "$*"; rc=1; }

# Root inside the VM via the guest agent (tobias can't read the system journal).
gx() { ssh -o BatchMode=yes "$PVE" "qm guest exec $VMID --timeout 60 -- bash -c $(printf %q "$1")" | jq -r '."out-data" // ""'; }

if ssh -o BatchMode=yes "$PVE" "qm agent $VMID ping" 2>/dev/null; then ok "guest agent answers"; else bad "guest agent ping"; fi

boots=$(gx 'journalctl --list-boots --no-pager | tail -2')
printf '      boots:\n%s\n' "$(sed 's/^/        /' <<<"$boots")"
prev=$(gx 'journalctl -b -1 -n 50 --no-pager -o short-iso')
if grep -q 'Reached target poweroff.target' <<<"$prev" && grep -q 'Journal stopped' <<<"$prev"; then
  ok "previous boot ended with a clean poweroff at $(tail -1 <<<"$prev" | cut -d' ' -f1)"
else
  bad "no clean poweroff in the previous boot's last 50 journal lines; tail:"
  tail -5 <<<"$prev" | sed 's/^/        /'
fi

boot_epoch=$(gx 'date -d "$(uptime -s)" +%s' | tr -d '[:space:]')
printf '      current boot: %s\n' "$(date -d "@$boot_epoch" '+%F %T %Z')"

# Every service must be running, started on its own within 10 min of boot.
want="db redis web worker backup"
ps_out=$(ssh -o BatchMode=yes "$VM" 'cd /opt/sure && docker compose --profile backup ps -a --format "{{.Service}} {{.State}} {{.Health}}"')
starts=$(ssh -o BatchMode=yes "$VM" 'cd /opt/sure && for c in $(docker compose --profile backup ps -aq); do docker inspect --format "{{index .Config.Labels \"com.docker.compose.service\"}} {{.State.StartedAt}} {{.HostConfig.RestartPolicy.Name}}" "$c"; done')
for s in $want; do
  line=$(awk -v s="$s" '$1==s' <<<"$ps_out" | head -1)
  state=$(awk '{print $2}' <<<"$line"); health=$(awk '{print $3}' <<<"$line")
  read -r _ started policy < <(awk -v s="$s" '$1==s' <<<"$starts")
  start_epoch=$(date -d "${started:-1970-01-01}" +%s 2>/dev/null || echo 0)
  delta=$(( start_epoch - ${boot_epoch:-0} ))
  if [ "$state" != running ]; then bad "$s is '${state:-missing}'"; continue; fi
  case "$s" in db|redis) [ "$health" = healthy ] || { bad "$s running but health='$health'"; continue; } ;; esac
  if [ "$delta" -lt 0 ] || [ "$delta" -gt 600 ]; then
    bad "$s started $(date -d "@$start_epoch" '+%T'), ${delta}s after boot (manual start or restart?)"
  else
    ok "$s running${health:+ ($health)}, came up ${delta}s after boot, restart=$policy"
  fi
done

mnt=$(gx 'findmnt -no UUID,TARGET /srv/sure-backups')
if grep -q '^832052b7-81ff-401a-8d6a-bc9fe6816eda /srv/sure-backups' <<<"$mnt"; then ok "backup disk mounted at /srv/sure-backups"; else bad "backup disk NOT mounted (got: '${mnt}')"; fi

latest=$(gx 'find /srv/sure-backups -mindepth 2 -maxdepth 2 -type d -name "*-scheduled" -printf "%T@ %p\n" | sort -n | tail -1')
if [ -z "$latest" ]; then
  bad "no scheduled backup yet (runs 18:00 UTC = 13:00 CDT / 12:00 CST)"
else
  age_h=$(( ( $(date +%s) - ${latest%%.*} ) / 3600 ))
  dir=${latest#* }
  sums=$(gx "cd '$dir' && sha256sum -c --quiet SHA256SUMS && echo SUMS_OK")
  if [ "$age_h" -le 26 ] && grep -q SUMS_OK <<<"$sums"; then ok "latest scheduled backup ${dir##*/} is ${age_h}h old, checksums OK"
  else bad "latest scheduled backup ${dir##*/} is ${age_h}h old; checksums: ${sums:-FAILED}"; fi
fi

code=$(curl -sS -m 15 -o /dev/null -w '%{http_code}' "$URL" 2>/dev/null)
case "$code" in 2??|3??) ok "$URL answers $code over trusted TLS" ;; *) bad "$URL answered '$code'" ;; esac

[ "$rc" -eq 0 ] && echo "RESULT: power cycle survived" || echo "RESULT: something needs a look"
exit "$rc"
