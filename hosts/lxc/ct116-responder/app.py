"""Responder HTTP service (CT 116, :8787). Runs as `responder` under systemd.

  POST /alert                     Checkmk intake: source IP + bearer token required
  POST /approve/<job>/<token>     phone button
  POST /deny/<job>/<token>        phone button
  POST /revoke/<grant>/<token>    phone button on auto-run notifications
  GET  /healthz

Config comes from the environment (EnvironmentFile=/etc/responder/responder.env, 640).
Every decision is logged to the journal (SyslogIdentifier=responder) for Wazuh.
"""
import hmac
import json
import logging
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import diagnose
import executor
import grants
import journal
import notify
import store
from registry import Registry

log = logging.getLogger("responder")

DB = os.environ.get("RESPONDER_DB", "/var/lib/responder/responder.db")
BIND = os.environ.get("BIND", "192.168.10.216")
PORT = int(os.environ.get("PORT", "8787"))
PUBLIC_BASE = os.environ.get("PUBLIC_BASE", f"http://{BIND}:{PORT}")
ALERT_SOURCES = set(os.environ.get("ALERT_SOURCES", "192.168.10.215").split())
APPROVAL_TTL = int(os.environ.get("APPROVAL_TTL", "1800"))
DEDUPE_WINDOW = int(os.environ.get("DEDUPE_WINDOW", "3600"))
JOBS_PER_HOUR = int(os.environ.get("JOBS_PER_HOUR", "6"))
MAX_BODY = 16384

ACT_ON = {"CRIT", "CRITICAL", "UNKNOWN", "DOWN", "UNREACHABLE"}
TAP = re.compile(r"^/(approve|deny)/([0-9a-f]{12})/([A-Za-z0-9_-]{32})$")
REVOKE = re.compile(r"^/revoke/([0-9a-f]{12})/([A-Za-z0-9_-]{32})$")
HOSTNAME = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

REGISTRY = Registry.load(os.environ.get("REGISTRY", "/etc/responder/registry.toml"))
DIAGNOSIS_SLOT = threading.Semaphore(1)  # one Claude session at a time


def now():
    return int(time.time())


def db():
    conn = store.connect(DB)
    grants.ensure_schema(conn)
    return conn


def verdict(d):
    lines = [f"**Diagnosis ({d['confidence']} confidence):** {d['diagnosis']}", "", f"**Rationale:** {d['rationale']}"]
    if d["proposal"]:
        host, verb, unit = d["proposal"]
        lines += ["", f"**Proposed action:** `{verb} {unit}` on `{host}`"]
    return "\n".join(lines)


def label(job):
    return f"{job['host']} / {job['service']}" if job["service"] else f"{job['host']} (host)"


# --- background work -------------------------------------------------------------------------

def handle_new_job(job_id):
    conn = db()
    try:
        job = store.get(conn, job_id)
        if store.jobs_created_since(conn, now() - 3600) > JOBS_PER_HOUR:
            log.warning("job=%s rate-limited, not diagnosing", job_id)
            notify.publish(f"Responder: {label(job)}", "Rate limit reached: not diagnosing this one."
                           " The plain Checkmk alert has the details.", tags=["hourglass"])
            return
        alerts = conn.execute("SELECT * FROM alerts WHERE job_id = ? ORDER BY id", (job_id,)).fetchall()
        log.info("job=%s diagnosing %s", job_id, label(job))
        with DIAGNOSIS_SLOT:
            d = diagnose.run(job, alerts, REGISTRY)
        log.info("job=%s diagnosis ok=%s proposal=%s confidence=%s transcript=%s error=%s",
                 job_id, d["ok"], d["proposal"], d["confidence"], d["transcript"], d["error"])

        job = store.get(conn, job_id)
        if job["state"] != "open":  # recovered (or closed) while Claude was thinking
            log.info("job=%s state=%s after diagnosis, nothing to propose", job_id, job["state"])
            notify.publish(f"Cleared: {label(job)}", f"{d['diagnosis'] or 'Recovered during diagnosis.'}",
                           priority="low", tags=["white_check_mark"])
            journal.record(job, "diagnosis", verdict(d) + "\n\nThe problem cleared before any action was needed.")
            return
        if not d["ok"]:
            notify.publish(f"Responder: {label(job)}", f"Diagnosis failed: {d['error']}", tags=["warning"])
            journal.record(job, "diagnosis", f"Diagnosis failed: {d['error']}")
            return
        if not d["proposal"]:
            notify.publish(f"Diagnosis: {label(job)}",
                           f"{d['diagnosis']}\n\nNo action proposed ({d['confidence']} confidence).",
                           tags=["mag"])
            journal.record(job, "diagnosis", verdict(d) + "\n\nNo action proposed: diagnosis only.")
            return

        host, verb, unit = d["proposal"]
        grant_id, reason = grants.check_auto(conn, REGISTRY, host, verb, unit, now())
        if grant_id and store.auto_approve(conn, job_id, verb, unit, now()):
            log.info("job=%s auto-approved by grant=%s (%s %s on %s)", job_id, grant_id, verb, unit, host)
            journal.record(job, "diagnosis", verdict(d))
            run_id = grants.start_auto_run(conn, grant_id, job_id, now())
            ok, detail = run_execution(conn, job_id, host)
            grants.finish_auto_run(conn, run_id, grant_id, ok, now())
            revoke_token = grants.revoke_link(conn, grant_id)
            demoted = "" if ok else "\nThis action is no longer remembered; next time it will ask."
            notify.publish(f"{'Auto-fixed' if ok else 'Auto-fix FAILED'}: {label(job)}",
                           f"{d['diagnosis']}\n\nRan {verb} {unit} on {host} (remembered approval): "
                           f"{detail}{demoted}",
                           priority="default" if ok else "high",
                           tags=["robot"] if ok else ["x"],
                           actions=[("Revoke", f"{PUBLIC_BASE}/revoke/{grant_id}/{revoke_token}")] if ok else [])
            journal.record(job, "auto-run", f"Ran `{verb} {unit}` on `{host}` without a tap (remembered approval,"
                           f" grant `{grant_id}`). Result: {detail}.{demoted}")
            return

        token = store.propose(conn, job_id, verb, unit, now(), APPROVAL_TTL)
        if token is None:
            return
        why = {grants.PROTECTED: "\nProtected target: approval runs once and is not remembered.",
               grants.TUPLE_LIMIT: "\nAuto-run limit reached for this action (2 per 24h): asking instead.",
               grants.GLOBAL_LIMIT: "\nGlobal auto-run limit reached: asking instead."}.get(reason, "")
        log.info("job=%s proposed %s %s on %s (auto: %s)", job_id, verb, unit, host, reason)
        journal.record(job, "diagnosis", verdict(d) + f"\n\nSent to the phone for approval (auto-run: {reason}).")
        notify.publish(f"Approve? {verb} {host}",
                       f"{label(job)}\n{d['diagnosis']}\n\nProposed: {verb} {unit} on {host}"
                       f" ({d['confidence']} confidence). Expires in {APPROVAL_TTL // 60} min.{why}",
                       priority="high", tags=["question"],
                       actions=[("Approve", f"{PUBLIC_BASE}/approve/{job_id}/{token}"),
                                ("Deny", f"{PUBLIC_BASE}/deny/{job_id}/{token}")])
    except Exception:
        log.exception("job=%s handler crashed", job_id)
    finally:
        conn.close()


def run_execution(conn, job_id, host):
    """Second guard: only the caller that moves approved -> executing may run anything."""
    if not store.start_execution(conn, job_id, now()):
        log.warning("job=%s execution refused: not in approved state", job_id)
        return False, "not executed (job no longer approved)"
    job = store.get(conn, job_id)
    log.info("job=%s executing %s %s on %s", job_id, job["verb"], job["unit"], host)
    ok, detail = executor.execute(REGISTRY.host(host), job["verb"])
    store.close(conn, job_id, "done" if ok else "failed", now())
    log.info("job=%s execution ok=%s detail=%s", job_id, ok, detail)
    return ok, detail


def handle_approved(job_id):
    conn = db()
    try:
        job = store.get(conn, job_id)
        host = REGISTRY.by_checkmk_name(job["host"])
        ok, detail = run_execution(conn, job_id, host)
        remembered = ""
        if ok:
            gid = grants.record(conn, REGISTRY, host, job["verb"], job["unit"], job_id, now())
            remembered = ("\nRemembered: this exact action will auto-run next time." if gid
                          else "\nProtected target: not remembered.")
            log.info("job=%s grant=%s", job_id, gid)
        journal.record(job, "approved", f"Approved from the phone. Ran `{job['verb']} {job['unit']}` on `{host}`."
                       f" Result: {detail}.{remembered}")
        notify.publish(f"{'Fixed' if ok else 'FAILED'}: {label(job)}",
                       f"{job['verb']} {job['unit']} on {host}: {detail}{remembered}",
                       priority="default" if ok else "high", tags=["white_check_mark"] if ok else ["x"])
    except Exception:
        log.exception("job=%s approved handler crashed", job_id)
    finally:
        conn.close()


def sweeper():
    while True:
        time.sleep(60)
        try:
            conn = db()
            for job_id in store.expire_due(conn, now()):
                store.close(conn, job_id, "expired", now())
                log.info("job=%s proposal expired, closed", job_id)
                journal.record(store.get(conn, job_id), "expired", "No decision before the approval window closed. Nothing ran.")
            conn.close()
        except Exception:
            log.exception("sweeper failed")


def spawn(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()


# --- HTTP ------------------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "responder"
    sys_version = ""

    def reply(self, code, text):
        body = (text + "\n").encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # access log -> journal, without query strings or tokens
        log.debug("http %s %s", self.client_address[0], fmt % args)

    def do_GET(self):
        if self.path == "/healthz":
            return self.reply(200, "ok")
        self.reply(404, "not found")

    def do_POST(self):
        src = self.client_address[0]
        if self.path == "/alert":
            return self.alert(src)
        m = TAP.match(self.path)
        if m:
            return self.tap(src, *m.groups())
        m = REVOKE.match(self.path)
        if m:
            return self.revoke(src, *m.groups())
        log.warning("refused src=%s reason=unknown-path", src)
        self.reply(404, "not found")

    def alert(self, src):
        auth = self.headers.get("Authorization", "")
        expected = f"Bearer {os.environ['ALERT_TOKEN']}"
        if src not in ALERT_SOURCES or not hmac.compare_digest(auth.encode(), expected.encode()):
            log.warning("refused src=%s reason=%s", src, "source" if src not in ALERT_SOURCES else "auth")
            return self.reply(403, "forbidden")
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return self.reply(400, "bad length")
        try:
            a = json.loads(self.rfile.read(n))
            host, service = str(a["host"]), str(a.get("service") or "")
            ntype, state, output = str(a["type"]), str(a["state"]).upper(), str(a.get("output", ""))
        except (ValueError, KeyError, TypeError):
            return self.reply(400, "bad json")
        if not HOSTNAME.match(host) or len(service) > 200:
            return self.reply(400, "bad host/service")
        conn = db()
        try:
            if ntype == "RECOVERY":
                closed = store.recover(conn, host, service, now())
                log.info("recovery %s/%s closed=%s", host, service, closed)
                return self.reply(200, f"recovered {len(closed)}")
            if ntype not in ("PROBLEM", "CUSTOM") or state not in ACT_ON:
                log.info("ignored %s %s/%s state=%s", ntype, host, service, state)
                return self.reply(200, "ignored")
            job_id, is_new = store.intake_alert(conn, host, service, ntype, state, output,
                                                now(), DEDUPE_WINDOW)
            log.info("alert %s/%s state=%s job=%s new=%s", host, service, state, job_id, is_new)
            if is_new:
                spawn(handle_new_job, job_id)
            return self.reply(200, f"job {job_id} {'new' if is_new else 'attached'}")
        finally:
            conn.close()

    def tap(self, src, action, job_id, token):
        decision = "approved" if action == "approve" else "denied"
        conn = db()
        try:
            result, state = store.claim(conn, job_id, token, decision, now())
            if result == store.CLAIMED:
                log.info("job=%s %s src=%s", job_id, decision, src)
                if decision == "approved":
                    spawn(handle_approved, job_id)
                    return self.reply(200, "approved: running")
                store.close(conn, job_id, "denied", now())
                journal.record(store.get(conn, job_id), "denied", "Denied from the phone. Nothing ran.")
                return self.reply(200, "denied")
            if result == store.INVALID:
                log.warning("job=%s refused-tap action=%s src=%s reason=invalid", job_id, action, src)
                return self.reply(403, "invalid")
            log.info("job=%s stale-tap action=%s state=%s result=%s src=%s", job_id, action, state, result, src)
            return self.reply(200, f"already handled: {state}")
        finally:
            conn.close()

    def revoke(self, src, grant_id, token):
        conn = db()
        try:
            result = grants.revoke(conn, grant_id, token, now())
            log.info("grant=%s revoke result=%s src=%s", grant_id, result, src)
            return self.reply(403 if result == "invalid" else 200, result.replace("_", " "))
        finally:
            conn.close()


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(message)s")
    conn = db()
    for job_id in store.interrupted(conn, now()):
        log.warning("job=%s was executing at shutdown: closed as interrupted", job_id)
    conn.close()
    spawn(sweeper)
    journal.flush_async()  # push anything queued before a restart or power cycle
    srv = ThreadingHTTPServer((BIND, PORT), Handler)
    log.info("listening on %s:%d, registry hosts=%s", BIND, PORT, sorted(REGISTRY.hosts))
    srv.serve_forever()


if __name__ == "__main__":
    main()
