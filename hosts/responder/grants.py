"""Learned approvals (§3a): an exact (host, verb, unit) approved once may auto-run later.

Lives in the same SQLite file as store.py (owned by `responder`, unreadable by
the Claude user). Claude never writes here; only the executor does, after a
manual approval succeeded.
"""
import hashlib
import hmac
import secrets

SCHEMA = """
CREATE TABLE IF NOT EXISTS grants (
    id            TEXT PRIMARY KEY,
    host          TEXT NOT NULL,
    verb          TEXT NOT NULL,
    unit          TEXT NOT NULL,
    created_at    INTEGER NOT NULL,
    approved_job  TEXT NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1,
    ended_at      INTEGER,
    end_reason    TEXT,
    UNIQUE (host, verb, unit)
);
CREATE TABLE IF NOT EXISTS auto_runs (
    id        INTEGER PRIMARY KEY,
    grant_id  TEXT NOT NULL REFERENCES grants (id),
    job_id    TEXT NOT NULL,
    ran_at    INTEGER NOT NULL,
    ok        INTEGER
);
CREATE TABLE IF NOT EXISTS revoke_links (
    token_hash TEXT PRIMARY KEY,
    grant_id   TEXT NOT NULL REFERENCES grants (id)
);
"""

PER_TUPLE_24H = 2   # a third auto-run inside 24 h falls back to a manual approval
GLOBAL_PER_HOUR = 4

# check_auto() reasons when it says no
NO_GRANT = "no-grant"
PROTECTED = "protected"
TUPLE_LIMIT = "tuple-limit"
GLOBAL_LIMIT = "global-limit"


def ensure_schema(conn):
    conn.executescript(SCHEMA)


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def record(conn, registry, host, verb, unit, job_id, now):
    """Remember a manually approved, successfully verified action. Returns grant id or None.

    Protected targets are never remembered, whatever the caller asks.
    """
    if registry.is_protected(host):
        return None
    row = conn.execute(
        "SELECT id FROM grants WHERE host = ? AND verb = ? AND unit = ?", (host, verb, unit)
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE grants SET active = 1, ended_at = NULL, end_reason = NULL,"
            " approved_job = ?, created_at = ? WHERE id = ?",
            (job_id, now, row["id"]),
        )
        return row["id"]
    grant_id = secrets.token_hex(6)
    conn.execute(
        "INSERT INTO grants (id, host, verb, unit, created_at, approved_job) VALUES (?, ?, ?, ?, ?, ?)",
        (grant_id, host, verb, unit, now, job_id),
    )
    return grant_id


def check_auto(conn, registry, host, verb, unit, now):
    """May this exact action run without a tap right now? Returns (grant_id | None, reason)."""
    if registry.is_protected(host):
        return None, PROTECTED
    row = conn.execute(
        "SELECT id FROM grants WHERE host = ? AND verb = ? AND unit = ? AND active = 1",
        (host, verb, unit),
    ).fetchone()
    if not row:
        return None, NO_GRANT
    recent = conn.execute(
        "SELECT COUNT(*) FROM auto_runs WHERE grant_id = ? AND ran_at > ?", (row["id"], now - 86400)
    ).fetchone()[0]
    if recent >= PER_TUPLE_24H:
        return None, TUPLE_LIMIT
    hour = conn.execute("SELECT COUNT(*) FROM auto_runs WHERE ran_at > ?", (now - 3600,)).fetchone()[0]
    if hour >= GLOBAL_PER_HOUR:
        return None, GLOBAL_LIMIT
    return row["id"], "ok"


def start_auto_run(conn, grant_id, job_id, now):
    """Count the run before it happens, so a crash mid-run still uses up the budget."""
    return conn.execute(
        "INSERT INTO auto_runs (grant_id, job_id, ran_at) VALUES (?, ?, ?)", (grant_id, job_id, now)
    ).lastrowid


def finish_auto_run(conn, run_id, grant_id, ok, now):
    """A failed verification demotes the grant back to manual approval."""
    conn.execute("UPDATE auto_runs SET ok = ? WHERE id = ?", (1 if ok else 0, run_id))
    if not ok:
        end(conn, grant_id, "verify-failed", now)


def end(conn, grant_id, reason, now):
    cur = conn.execute(
        "UPDATE grants SET active = 0, ended_at = ?, end_reason = ? WHERE id = ? AND active = 1",
        (now, reason, grant_id),
    )
    return cur.rowcount == 1


def revoke_link(conn, grant_id):
    """A fresh token for a Revoke button. Only its hash is stored."""
    token = secrets.token_urlsafe(24)
    conn.execute("INSERT INTO revoke_links (token_hash, grant_id) VALUES (?, ?)", (_hash(token), grant_id))
    return token


def revoke(conn, grant_id, token, now):
    """Returns 'revoked', 'already_revoked' or 'invalid'."""
    row = conn.execute(
        "SELECT grant_id FROM revoke_links WHERE token_hash = ?", (_hash(token),)
    ).fetchone()
    if row is None or not hmac.compare_digest(row["grant_id"], grant_id):
        return "invalid"
    return "revoked" if end(conn, grant_id, "revoked", now) else "already_revoked"
