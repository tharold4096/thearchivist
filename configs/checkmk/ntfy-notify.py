#!/usr/bin/env python3
# ntfy (homelab)
#
# CheckMK notification plugin: push to self-hosted ntfy (CT 102).
# Install: ~monitoring/local/share/check_mk/notifications/ntfy (mode 755)
# Token:   ~monitoring/etc/ntfy-token (mode 600, ntfy user `checkmk`,
#          write-only on topic `homelab-alerts`). Never commit the token.
#
# Posts to the ntfy CT IP directly, NOT via Caddy, so a Caddy outage
# can still be alerted on.

import os
import sys
import urllib.error
import urllib.request

NTFY_URL = "http://192.168.10.203/homelab-alerts"
TOKEN_FILE = os.path.expanduser("~/etc/ntfy-token")
CMK_URL = "https://checkmk.home.arpa/monitoring/check_mk/"

e = os.environ.get
what = e("NOTIFY_WHAT", "SERVICE")
ntype = e("NOTIFY_NOTIFICATIONTYPE", "PROBLEM")
host = e("NOTIFY_HOSTNAME", "?")

if what == "HOST":
    state = e("NOTIFY_HOSTSTATE", "?")
    subject = host
    output = e("NOTIFY_HOSTOUTPUT", "")
    link = f"{CMK_URL}index.py?start_url=view.py%3Fview_name%3Dhost%26host%3D{host}"
else:
    state = e("NOTIFY_SERVICESTATE", "?")
    subject = f"{host} / {e('NOTIFY_SERVICEDESC', '?')}"
    output = e("NOTIFY_SERVICEOUTPUT", "")
    link = f"{CMK_URL}index.py?start_url=view.py%3Fview_name%3Dhost%26host%3D{host}"

if ntype == "RECOVERY":
    prio, tags = "3", "white_check_mark"
elif state in ("DOWN", "UNREACHABLE"):
    prio, tags = "5", "rotating_light"
elif state == "CRITICAL":
    prio, tags = "4", "red_circle"
elif state == "UNKNOWN":
    prio, tags = "3", "grey_question"
else:
    prio, tags = "3", "warning"

title = f"{state}: {subject}"
if ntype not in ("PROBLEM", "RECOVERY"):
    title = f"[{ntype}] {title}"
body = f"{output}\n{e('NOTIFY_SHORTDATETIME', '')}".strip()

try:
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
except OSError as exc:
    sys.stderr.write(f"cannot read token: {exc}\n")
    sys.exit(2)

req = urllib.request.Request(
    NTFY_URL,
    data=body.encode(),
    method="POST",
    headers={
        "Authorization": f"Bearer {token}",
        "Title": title.encode("utf-8").decode("latin-1", "replace"),
        "Priority": prio,
        "Tags": tags,
        "Click": link,
    },
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(f"ntfy: HTTP {r.status}")
except urllib.error.HTTPError as exc:
    sys.stderr.write(f"ntfy HTTP {exc.code}: {exc.read()[:200]!r}\n")
    sys.exit(2 if 400 <= exc.code < 500 else 1)
except Exception as exc:  # network errors: let CheckMK retry
    sys.stderr.write(f"ntfy error: {exc}\n")
    sys.exit(1)
