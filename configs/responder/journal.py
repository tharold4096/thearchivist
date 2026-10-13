"""Publish what the responder did to the public repo, under journal/responder/.

Deterministic code, not Claude: it renders Claude's structured verdict plus the
executor's result into markdown and pushes it with a dedicated deploy key.
The repo is PUBLIC, so:
  - only summaries go out (diagnosis, rationale, action, result); raw transcripts and
    tool output stay in /var/lib/responder/transcripts
  - text passes a secret filter before it is written
  - arr-stack hosts are never published (house rule: arr docs stay local)
Failures never block alert handling. An auth failure pings the phone (at most every 6 h).
"""
import logging
import os
import re
import subprocess
import threading
import time

import notify

log = logging.getLogger("responder.journal")

REPO_URL = os.environ.get("JOURNAL_REPO", "git@github.com:tharold4096/thearchivist.git")
BRANCH = os.environ.get("JOURNAL_BRANCH", "main")
CLONE = "/var/lib/responder/journal-repo"
SUBDIR = "journal/responder"
SSH = ("ssh -i /home/responder/.ssh/journal_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes"
       " -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/etc/responder/known_hosts_github")
SKIP_HOSTS = {"sonarr", "radarr", "prowlarr", "seerr", "qbittorrent", "flaresolverr",
              "lidarr", "readarr", "bazarr"}
AUTH_PING_EVERY = 6 * 3600

_lock = threading.Lock()  # one git operation at a time
_last_auth_ping = 0.0

_SECRETS = [
    re.compile(r"tk_[A-Za-z0-9]{8,}"),                                   # ntfy tokens
    re.compile(r"(?i)(bearer|token|secret|password|passwd|api[_-]?key)(\s*[:=]\s*|\s+)\S+"),
    re.compile(r"homelab-(alerts|updates)-[a-z0-9]{6,}"),               # unguessable topic names
    re.compile(r"\b[A-Za-z0-9+/_-]{32,}={0,2}\b"),                        # long opaque strings
]


def scrub(text):
    for pat in _SECRETS:
        text = pat.sub("[redacted]", text)
    return text


def _git(*args, timeout=60):
    env = {**os.environ, "GIT_SSH_COMMAND": SSH, "GIT_TERMINAL_PROMPT": "0",
           "HOME": "/var/lib/responder"}
    return subprocess.run(["git", "-C", CLONE, *args], capture_output=True, text=True,
                          timeout=timeout, env=env)


def _ensure_clone():
    if os.path.isdir(os.path.join(CLONE, ".git")):
        return None
    env = {**os.environ, "GIT_SSH_COMMAND": SSH, "GIT_TERMINAL_PROMPT": "0", "HOME": "/var/lib/responder"}
    r = subprocess.run(["git", "clone", "--depth", "1", "--branch", BRANCH, "--filter=blob:none",
                        "--sparse", REPO_URL, CLONE], capture_output=True, text=True, timeout=120, env=env)
    if r.returncode != 0:
        return r.stderr
    _git("sparse-checkout", "set", SUBDIR)
    _git("config", "user.name", "Responder (CT 116)")
    _git("config", "user.email", "responder@thearchivist.home.arpa")
    return None


def _auth_problem(stderr):
    global _last_auth_ping
    log.error("journal push failed: %s", stderr.strip()[-300:])
    if any(s in stderr for s in ("Permission denied", "publickey", "Repository not found",
                                 "denied to deploy key", "Host key verification failed")):
        if time.time() - _last_auth_ping > AUTH_PING_EVERY:
            _last_auth_ping = time.time()
            notify.publish("Responder journal: GitHub auth needed",
                           "The responder can't push its journal to the repo (deploy key rejected or"
                           " missing). Records are queued locally on CT 116 until it works.",
                           priority="high", tags=["key"])


def _publish(relpath, text, message):
    with _lock:
        err = _ensure_clone()
        if err:
            return _auth_problem(err)
        # Rebase, never reset: commits that failed to push earlier (e.g. auth outage) stay
        # queued on top and go out with the next successful push.
        if _git("fetch", "--depth", "1", "origin", BRANCH).returncode == 0:
            if _git("rebase", f"origin/{BRANCH}").returncode != 0:
                _git("rebase", "--abort")
        path = os.path.join(CLONE, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(text)
        _git("add", "--sparse", relpath)
        r = _git("commit", "-q", "-m", message)
        if r.returncode != 0:
            log.error("journal commit failed: %s", (r.stdout + r.stderr).strip()[-300:])
            return
        for _ in range(3):
            r = _git("push", "-q", "origin", f"HEAD:{BRANCH}")
            if r.returncode == 0:
                log.info("journal pushed %s", relpath)
                return
            if "rejected" in r.stderr or "fetch first" in r.stderr:
                _git("fetch", "--depth", "1", "origin", BRANCH)
                if _git("rebase", f"origin/{BRANCH}").returncode != 0:
                    _git("rebase", "--abort")
                continue
            return _auth_problem(r.stderr)
        log.error("journal push gave up after retries: %s", relpath)


def record(job, event, body):
    """Append one event section to the job's journal file and push it, in the background."""
    if job["host"] in SKIP_HOSTS:
        log.info("job=%s journal skipped (arr-stack host)", job["id"])
        return
    day = time.strftime("%Y-%m-%d", time.localtime(job["created_at"]))
    relpath = f"{SUBDIR}/{day[:4]}/{day[5:7]}/{day}-{job['host']}-{job['id']}.md"
    stamp = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    header = ""
    if event == "diagnosis":
        header = (f"# {job['host']} / {job['service'] or '(host check)'}\n\n"
                  f"Job `{job['id']}`, opened {time.strftime('%Y-%m-%d %H:%M %Z', time.localtime(job['created_at']))}."
                  " Written automatically by the responder on CT 116.\n\n")
    text = header + f"## {stamp}: {event}\n\n{scrub(body).strip()}\n\n"
    msg = f"journal: {job['host']} {event} ({job['id']})"
    threading.Thread(target=_safe_publish, args=(relpath, text, msg), daemon=True).start()


def _safe_publish(relpath, text, message):
    try:
        _publish(relpath, text, message)
    except Exception:
        log.exception("journal publish crashed")
