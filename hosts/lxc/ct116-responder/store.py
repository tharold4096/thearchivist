"""Responder job state: one SQLite row per problem (host + service).

Every state change is a single guarded UPDATE (``... WHERE state = <expected>``).
When two callers race (two taps on the same button, two alerts, two executors)
exactly one sees rowcount == 1 and owns the transition; the others get 0 and
back off. That is the whole double-tap / double-execution guarantee.

States:
  open       alert received, no proposal yet (or diagnosis-only)
  pending    proposal sent to the phone, waiting for Approve/Deny
  approved   claimed by an Approve tap
  denied     claimed by a Deny tap
  expired    proposal not decided before expires_at
  executing  the executor has taken the approved job
  closed     terminal; close_reason says why

Callers pass ``now`` (epoch seconds) so tests control time. Use one connection
per thread: sqlite3 connections must not be shared across threads.
"""
import contextlib
import hashlib
import hmac
import secrets
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id           TEXT PRIMARY KEY,
    dedupe_key   TEXT NOT NULL,
    host         TEXT NOT NULL,
    service      TEXT NOT NULL,
    state        TEXT NOT NULL CHECK (state IN
                   ('open', 'pending', 'approved', 'denied', 'expired', 'executing', 'closed')),
    created_at   INTEGER NOT NULL,
    updated_at   INTEGER NOT NULL,
    closed_at    INTEGER,
    close_reason TEXT,
    verb         TEXT,
    unit         TEXT,
    token_hash   TEXT,
    expires_at   INTEGER
);
CREATE INDEX IF NOT EXISTS jobs_dedupe ON jobs (dedupe_key, state);
CREATE INDEX IF NOT EXISTS jobs_created ON jobs (created_at);
CREATE TABLE IF NOT EXISTS alerts (
    id                INTEGER PRIMARY KEY,
    job_id            TEXT NOT NULL REFERENCES jobs (id),
    received_at       INTEGER NOT NULL,
    notification_type TEXT NOT NULL,
    state             TEXT NOT NULL,
    output            TEXT NOT NULL
);
"""

OUTPUT_MAX = 4096  # bytes of Checkmk plugin output kept per alert

# claim() results
CLAIMED = "claimed"
ALREADY_HANDLED = "already_handled"
INVALID = "invalid"
EXPIRED = "expired"


def connect(path):
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


@contextlib.contextmanager
def _immediate(conn):
    """Write transaction that takes the lock up front, so read-then-insert can't interleave."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def dedupe_key(host, service):
    return f"{host}\x1f{service}"


def get(conn, job_id):
    return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def jobs_created_since(conn, since):
    """For the global rate limit: how many jobs were opened after ``since``."""
    return conn.execute("SELECT COUNT(*) FROM jobs WHERE created_at > ?", (since,)).fetchone()[0]


def intake_alert(conn, host, service, notification_type, state, output, now, window):
    """Attach an alert to the live job for host+service, or open a new job.

    A job is live if it isn't closed, or if it closed less than ``window``
    seconds ago for any reason other than recovery (a denied or expired
    problem that re-fires shouldn't start a fresh session straight away).

    Returns (job_id, is_new). Only is_new=True may start a diagnosis.
    """
    key = dedupe_key(host, service)
    with _immediate(conn):
        row = conn.execute(
            "SELECT id FROM jobs WHERE dedupe_key = ?"
            " AND (state != 'closed' OR (close_reason != 'recovered' AND closed_at > ?))"
            " ORDER BY created_at DESC LIMIT 1",
            (key, now - window),
        ).fetchone()
        if row:
            job_id, is_new = row["id"], False
        else:
            job_id, is_new = secrets.token_hex(6), True
            conn.execute(
                "INSERT INTO jobs (id, dedupe_key, host, service, state, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, 'open', ?, ?)",
                (job_id, key, host, service, now, now),
            )
        conn.execute(
            "INSERT INTO alerts (job_id, received_at, notification_type, state, output)"
            " VALUES (?, ?, ?, ?, ?)",
            (job_id, now, notification_type, state, output[:OUTPUT_MAX]),
        )
    return job_id, is_new


def propose(conn, job_id, verb, unit, now, ttl):
    """open -> pending. Returns the approval token, or None if the job isn't open.

    The token goes into the notification's button URLs and is never stored;
    only its hash is, so a copy of the DB can't approve anything.
    """
    token = secrets.token_urlsafe(24)
    cur = conn.execute(
        "UPDATE jobs SET state = 'pending', verb = ?, unit = ?, token_hash = ?,"
        " expires_at = ?, updated_at = ? WHERE id = ? AND state = 'open'",
        (verb, unit, _hash(token), now + ttl, now, job_id),
    )
    return token if cur.rowcount == 1 else None


def claim(conn, job_id, token, decision, now):
    """pending -> approved|denied, for exactly one caller.

    Returns (result, state):
      (CLAIMED, decision)       this call won; act on it
      (ALREADY_HANDLED, state)  a valid token, but the job was already decided
      (EXPIRED, 'expired')      a valid token, too late
      (INVALID, None)           unknown job or wrong token
    """
    if decision not in ("approved", "denied"):
        raise ValueError(f"bad decision: {decision!r}")
    row = conn.execute(
        "SELECT state, token_hash, expires_at FROM jobs WHERE id = ?", (job_id,)
    ).fetchone()
    if row is None or row["token_hash"] is None:
        return INVALID, None
    if not hmac.compare_digest(_hash(token), row["token_hash"]):
        return INVALID, None
    if row["state"] == "pending" and now >= row["expires_at"]:
        conn.execute(
            "UPDATE jobs SET state = 'expired', updated_at = ? WHERE id = ? AND state = 'pending'",
            (now, job_id),
        )
        return EXPIRED, "expired"
    cur = conn.execute(
        "UPDATE jobs SET state = ?, updated_at = ?"
        " WHERE id = ? AND state = 'pending' AND expires_at > ?",
        (decision, now, job_id, now),
    )
    if cur.rowcount == 1:
        return CLAIMED, decision
    return ALREADY_HANDLED, get(conn, job_id)["state"]


def auto_approve(conn, job_id, verb, unit, now):
    """open -> approved, for a remembered action (grants.check_auto said yes). No token involved."""
    cur = conn.execute(
        "UPDATE jobs SET state = 'approved', verb = ?, unit = ?, updated_at = ?"
        " WHERE id = ? AND state = 'open'",
        (verb, unit, now, job_id),
    )
    return cur.rowcount == 1


def interrupted(conn, now):
    """At startup: jobs left 'executing' by a crash or power cycle. Close them; return ids."""
    rows = conn.execute("SELECT id FROM jobs WHERE state = 'executing'").fetchall()
    return [r["id"] for r in rows if close(conn, r["id"], "interrupted", now)]


def start_execution(conn, job_id, now):
    """approved -> executing. The executor may run the action only if this returns True.

    Second, independent guard against double execution: even if two workers
    were handed the same approved job, only one gets past here.
    """
    cur = conn.execute(
        "UPDATE jobs SET state = 'executing', updated_at = ? WHERE id = ? AND state = 'approved'",
        (now, job_id),
    )
    return cur.rowcount == 1


def close(conn, job_id, reason, now):
    """Any state -> closed. Idempotent; returns True only for the call that closed it."""
    cur = conn.execute(
        "UPDATE jobs SET state = 'closed', close_reason = ?, closed_at = ?, updated_at = ?"
        " WHERE id = ? AND state != 'closed'",
        (reason, now, now, job_id),
    )
    return cur.rowcount == 1


def recover(conn, host, service, now):
    """Checkmk RECOVERY: close every live job for host+service. Returns the closed ids.

    A job that is mid-execution is left for the executor to verify and close.
    An approved-but-not-started job is closed, so start_execution() then
    refuses it: nothing gets restarted after the problem has already cleared.
    """
    rows = conn.execute(
        "SELECT id FROM jobs WHERE dedupe_key = ? AND state NOT IN ('closed', 'executing')",
        (dedupe_key(host, service),),
    ).fetchall()
    return [r["id"] for r in rows if close(conn, r["id"], "recovered", now)]


def expire_due(conn, now):
    """pending past expires_at -> expired. Returns the ids this call expired."""
    rows = conn.execute(
        "SELECT id FROM jobs WHERE state = 'pending' AND expires_at <= ?", (now,)
    ).fetchall()
    expired = []
    for r in rows:
        cur = conn.execute(
            "UPDATE jobs SET state = 'expired', updated_at = ? WHERE id = ? AND state = 'pending'",
            (now, r["id"]),
        )
        if cur.rowcount == 1:
            expired.append(r["id"])
    return expired
