#!/usr/bin/env python3
# Responder (CT 116)
# Checkmk notification plugin: hand major alerts to the responder for diagnosis.
# Install: ~monitoring/local/share/check_mk/notifications/responder (mode 755)
# Auth:    ~monitoring/etc/responder.secret (mode 600) holds the bearer token. Never commit it.
#
# The plain ntfy rule stays in place alongside this one: if the responder is down,
# the phone still gets the alert (handoff §3.7).
import json
import os
import sys
import urllib.error
import urllib.request

URL = "http://192.168.10.216:8787/alert"
SECRET_FILE = os.path.expanduser("~/etc/responder.secret")


def e(name, default=""):
    return os.environ.get("NOTIFY_" + name, default)


what = e("WHAT")  # SERVICE or HOST
payload = {
    "what": what,
    "host": e("HOSTNAME"),
    "service": e("SERVICEDESC") if what == "SERVICE" else "",
    "type": e("NOTIFICATIONTYPE"),
    "state": e("SERVICESTATE") if what == "SERVICE" else e("HOSTSTATE"),
    "output": (e("SERVICEOUTPUT") if what == "SERVICE" else e("HOSTOUTPUT"))[:4000],
}

try:
    with open(SECRET_FILE) as f:
        secret = f.read().strip()
except OSError as exc:
    sys.stderr.write(f"cannot read responder secret: {exc}\n")
    sys.exit(2)

req = urllib.request.Request(
    URL,
    data=json.dumps(payload).encode(),
    method="POST",
    headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"responder: HTTP {resp.status} {resp.read(200).decode(errors='replace').strip()}")
except urllib.error.HTTPError as exc:
    sys.stderr.write(f"responder: HTTP {exc.code}\n")
    sys.exit(2)
except (urllib.error.URLError, OSError) as exc:
    sys.stderr.write(f"responder: unreachable: {exc}\n")
    sys.exit(2)
