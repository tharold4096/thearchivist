#!/bin/sh
# Undo step 1 (DNS enforcement). Nothing stops this; once sentry-dns-guard is
# running, every line below is reported to ntfy. Run as root.
set -x
nft delete table inet sentry_dns_lock
systemctl disable sentry-dns-lock.service
rm -f /etc/systemd/resolved.conf.d/50-sentry-dns.conf \
      /etc/NetworkManager/conf.d/50-sentry-dns.conf \
      /etc/chromium/policies/managed/sentry-dns.json
tailscale set --accept-dns=true
systemctl restart systemd-resolved
systemctl reload NetworkManager
# /etc/hosts tailnet lines: restore /etc/hosts.pre-sentry-dns by hand if wanted.
