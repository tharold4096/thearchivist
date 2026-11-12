"""Publish to ntfy (CT 102) as the write-only `responder` user.

URL and token come from the environment (EnvironmentFile=, mode 600), never from code:
the topic name is unguessable on purpose (iOS relay hash collision, 2026-10-12).
"""
import json
import os
import urllib.error
import urllib.request

PRIORITY = {"low": 2, "default": 3, "high": 4, "urgent": 5}


def publish(title, message, priority="default", tags=(), actions=()):
    """actions: list of (label, url) pairs -> ntfy `http` POST buttons. Returns True on 2xx."""
    body = {
        "topic": os.environ["NTFY_URL"].rstrip("/").rsplit("/", 1)[1],
        "title": title[:250],
        "message": message[:3800],
        "priority": PRIORITY.get(priority, 3),
        "tags": list(tags),
        "actions": [{"action": "http", "label": label, "url": url, "method": "POST"}
                    for label, url in actions],
    }
    base = os.environ["NTFY_URL"].rstrip("/").rsplit("/", 1)[0]
    req = urllib.request.Request(
        base,  # JSON publishing posts to the server root, topic in the body
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {os.environ['NTFY_TOKEN']}",
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, OSError):
        return False
