#!/usr/bin/env bash
# One read-only Sure API request. Prints the HTTP status and the JSON *shape*
# (keys and value types, first array element only), never the values.
# Usage: bash sure-api-check.sh [endpoint]     default: /api/v1/accounts
# Auth header is X-Api-Key (app/controllers/api/v1/base_controller.rb).
# The key is read silently (or from $SURE_API_KEY) and passed to curl on an
# fd, so it never appears in argv, history or output.
set -u
EP=${1:-/api/v1/accounts}
BASE=https://budget.home.arpa
if [ -z "${SURE_API_KEY:-}" ]; then read -rsp 'Sure API key: ' SURE_API_KEY; echo; fi
body=$(mktemp); trap 'rm -f "$body"' EXIT
code=$(curl -sS -m 20 -o "$body" -w '%{http_code}' -H 'Accept: application/json' -H @<(printf 'X-Api-Key: %s\n' "$SURE_API_KEY") "$BASE$EP")
echo "GET $EP -> HTTP $code"
jq 'def shape: if type == "object" then with_entries(.value |= shape)
              elif type == "array" then (if length > 0 then [(.[0] | shape), "...\(length) items"] else [] end)
              else type end;
    shape' "$body" 2>/dev/null || echo "(body is not JSON, $(wc -c <"$body") bytes)"
