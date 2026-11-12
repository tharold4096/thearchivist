#!/bin/bash
# Usage: probe.sh host:port [host:port ...]
# Opens one TCP connection per target, in parallel, and prints
#   <host:port> <up|partial|down> <milliseconds>
# per target. Sends no data. "partial" means the port did not answer but the
# host replied to one ping, so the machine is up and the service is not.
# Targets that are not a plain hostname/IPv4 and a port are reported down
# without being touched.

probe() {
  local target=$1 host=${1%:*} port=${1##*:} start=${EPOCHREALTIME/./}
  if [[ ! $host =~ ^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$ || ! $port =~ ^[0-9]{1,5}$ ]] || ((port < 1 || port > 65535)); then
    printf '%s down 0\n' "$target"
    return
  fi
  if timeout 3 bash -c 'exec 3<>"/dev/tcp/$1/$2"' _ "$host" "$port" 2>/dev/null; then
    printf '%s up %d\n' "$target" $(((${EPOCHREALTIME/./} - start) / 1000))
  elif ping -c 1 -W 2 -- "$host" >/dev/null 2>&1; then
    printf '%s partial 0\n' "$target"
  else
    printf '%s down 0\n' "$target"
  fi
}

for target in "${@:1:40}"; do
  probe "$target" &
done
wait
