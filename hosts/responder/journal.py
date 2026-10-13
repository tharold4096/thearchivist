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
import json
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
QUEUE = "/var/lib/responder/journal-queue"  # records not yet pushed; survives restarts
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
                           " missing). Records are queued on CT 116 and go out once it works.",
                           priority="high", tags=["key"])


def _flush():
    """Push every queued record. Never rebases: reset to the remote tip, re-apply the queue, push.

    A depth-1 clone has no merge base, so rebasing onto a moved main fails. Resetting and
    re-appending is always valid because records only ever append to per-job files. Queue
    entries are deleted only after a successful push, so auth outages and power cycles lose nothing.
    """
    with _lock:
        err = _ensure_clone()
        if err:
            return _auth_problem(err)
        for _ in range(3):
            entries = sorted(n for n in os.listdir(QUEUE) if n.endswith(".json")) if os.path.isdir(QUEUE) else []
            if not entries:
                return
            r = _git("fetch", "--depth", "1", "origin", BRANCH)
            if r.returncode != 0:
                return _auth_problem(r.stderr)
            _git("reset", "-q", "--hard", f"origin/{BRANCH}")
            messages = []
            for name in entries:
                with open(os.path.join(QUEUE, name)) as f:
                    e = json.load(f)
                path = os.path.join(CLONE, e["relpath"])
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "a") as f:
                    f.write(e["text"])
                _git("add", "--sparse", e["relpath"])
                messages.append(e["message"])
            msg = messages[0] if len(messages) == 1 else f"journal: {len(messages)} records\n\n" + "\n".join(messages)
            r = _git("commit", "-q", "-m", msg)
            if r.returncode != 0:
                log.error("journal commit failed: %s", (r.stdout + r.stderr).strip()[-300:])
                return
            r = _git("push", "-q", "origin", f"HEAD:{BRANCH}")
            if r.returncode == 0:
                for name in entries:
                    os.remove(os.path.join(QUEUE, name))
                log.info("journal pushed %d record(s)", len(entries))
                return
            if "rejected" not in r.stderr and "fetch first" not in r.stderr:
                return _auth_problem(r.stderr)
            time.sleep(2)  # main moved under us (e.g. a PR merge): reset and re-apply
        log.error("journal push still rejected after retries; %d record(s) stay queued", len(entries))


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
    os.makedirs(QUEUE, exist_ok=True)
    name = f"{time.time_ns()}-{job['id']}.json"
    with open(os.path.join(QUEUE, name + ".tmp"), "w") as f:
        json.dump({"relpath": relpath, "text": text, "message": msg}, f)
    os.rename(os.path.join(QUEUE, name + ".tmp"), os.path.join(QUEUE, name))
    flush_async()


def flush_async():
    threading.Thread(target=_safe_flush, daemon=True).start()


def _safe_flush():
    try:
        _flush()
    except Exception:
        log.exception("journal flush crashed")
