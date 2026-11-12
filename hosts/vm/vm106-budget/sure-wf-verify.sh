#!/usr/bin/env bash
# Verify a Wells Fargo CSV import in Sure. Read-only.
# Usage: bash sure-wf-verify.sh [path/to/wf-export.csv]
# With a CSV, also prints its row count and date range to compare against Sure.
# WF's current export has a header ("DATE","DESCRIPTION","AMOUNT","CHECK #","STATUS");
# older ones don't. Either way the date is column 1, and only rows starting with a
# MM/DD/YYYY date are counted, so a header line is never counted as a transaction.
set -u
here=$(cd "$(dirname "$0")" && pwd)
if [ -n "${1:-}" ]; then
  awk -F'","' 'NF >= 5 { d = substr($1, 2); if (d !~ /^[0-9][0-9]\/[0-9][0-9]\/[0-9][0-9][0-9][0-9]$/) next
                         split(d, p, "/"); k = p[3] p[1] p[2]; n++
                         if (!min || k < min) { min = k; mind = d }
                         if (k > max) { max = k; maxd = d } }
               END { printf "CSV  rows=%d range=%s..%s\n", n, mind, maxd }' "$1"
fi
ssh -o BatchMode=yes tobias@192.168.10.206 'cd /opt/sure && docker compose exec -T web bin/rails runner "$(cat)" 2>/dev/null' <"$here/sure-wf-verify.rb" | grep -vE '^[WI], \['
