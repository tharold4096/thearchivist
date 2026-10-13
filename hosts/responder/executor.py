"""Run an approved write verb through rgate and verify the result. Deterministic; no Claude here.

Uses the executor's own key (~responder/.ssh/gate_ed25519). On the target that key is pinned to
`command="/usr/local/bin/rgate"` (full mode). The Claude key is pinned to `rgate read`.
"""
import subprocess
import time
import urllib.error
import urllib.request

KEY = "/home/responder/.ssh/gate_ed25519"
KNOWN_HOSTS = "/home/responder/.ssh/known_hosts"


def gate(ip, verb, timeout=60):
    cmd = ["ssh", "-i", KEY, "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
           "-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
           "-o", "ConnectTimeout=10", "-T", f"rgate@{ip}", verb]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).decode(errors="replace")[:4000]
    except subprocess.TimeoutExpired:
        return None, "timeout"


def _active(ip):
    rc, out = gate(ip, "status", timeout=30)
    return rc == 0 and "ActiveState=active" in out.splitlines()


def _http_ok(url, expect):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return expect in resp.read(4096).decode(errors="replace")
    except (urllib.error.URLError, OSError):
        return False


def verify(host_cfg):
    """Poll until systemd is active AND the health URL answers as expected, or time runs out."""
    deadline = time.monotonic() + host_cfg.get("verify_timeout", 60)
    ip, url, expect = host_cfg["ip"], host_cfg.get("verify_url"), host_cfg.get("verify_expect", "")
    while time.monotonic() < deadline:
        if _active(ip) and (not url or _http_ok(url, expect)):
            return True
        time.sleep(3)
    return False


def execute(host_cfg, verb):
    """Returns (ok, detail). ok means the verb ran AND verification passed."""
    started = time.monotonic()
    rc, out = gate(host_cfg["ip"], verb)
    if rc != 0:
        return False, f"rgate {verb} failed (rc={rc}): {out.strip()[:300]}"
    if not verify(host_cfg):
        return False, f"{verb} ran but verification failed within {host_cfg.get('verify_timeout', 60)}s"
    return True, f"{verb} ok, verified in {time.monotonic() - started:.0f}s"
