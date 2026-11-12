"""Run one Claude diagnosis for a job and turn its answer into something the code can trust.

Claude runs as `rclaude` through the root-owned run-claude script (fixed flags, read-only
tools). Whatever comes back is validated against the registry here: a proposal that
doesn't name a registered write verb is dropped and the job becomes diagnosis-only.
"""
import json
import os
import subprocess
import time

TRANSCRIPTS = "/var/lib/responder/transcripts"
RUNNER = ["sudo", "-n", "-u", "rclaude", "/usr/local/lib/responder/run-claude"]
TIMEOUT = 330


def _untrusted(text):
    # Alert text can't close or open our delimiter tags.
    return text.replace("<", "‹").replace(">", "›")


def build_prompt(job, alerts, registry):
    lines = ["A monitoring alert fired. Diagnose it.", "",
             "Registered hosts (the only ones gate-read can reach, and the only valid proposal targets):"]
    for key, h in sorted(registry.hosts.items()):
        lines.append(f"- {key}: Checkmk name `{h['checkmk_name']}`, unit {h['unit']},"
                     f" read verbs {h['read_verbs']}, write verbs {h['write_verbs']}")
    reg_key = registry.by_checkmk_name(job["host"])
    lines += ["",
              f"This alert's host is {'registered as `' + reg_key + '`' if reg_key else 'NOT registered: proposed_action must be null'}.",
              "", "<untrusted_alert>"]
    for a in alerts:
        lines.append(_untrusted(
            f"{a['notification_type']} host={job['host']} service={job['service'] or '(host check)'}"
            f" state={a['state']} at={time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(a['received_at']))}\n"
            f"output: {a['output']}"))
    lines.append("</untrusted_alert>")
    return "\n".join(lines)


def run(job, alerts, registry):
    """Returns dict(diagnosis, confidence, proposal, rationale, ok, error).

    proposal is a validated (host, verb, unit) tuple or None.
    """
    prompt = build_prompt(job, alerts, registry)
    started = time.time()
    record = {"job_id": job["id"], "started": started, "prompt": prompt}
    try:
        r = subprocess.run(RUNNER, input=prompt.encode(), capture_output=True, timeout=TIMEOUT)
        record.update(rc=r.returncode, stdout=r.stdout.decode(errors="replace"),
                      stderr=r.stderr.decode(errors="replace")[-4000:])
    except subprocess.TimeoutExpired:
        record.update(rc=None, stdout="", stderr="timeout")
    record["seconds"] = round(time.time() - started, 1)

    result = {"diagnosis": "", "confidence": "low", "proposal": None, "rationale": "",
              "ok": False, "error": None}
    try:
        out = json.loads(record["stdout"])
        record["claude"] = out
        verdict = out.get("structured_output")
        if verdict is None:
            verdict = json.loads(out["result"])
        result.update(diagnosis=str(verdict["diagnosis"])[:600],
                      confidence=str(verdict.get("confidence", "low")),
                      rationale=str(verdict.get("rationale", ""))[:2000], ok=True)
        raw = verdict.get("proposed_action")
        result["proposal"] = registry.validate_proposal(raw)
        if raw and result["proposal"] is None:
            result["rationale"] += f"\n[responder] dropped out-of-registry proposal: {json.dumps(raw)[:200]}"
        if result["proposal"] and registry.by_checkmk_name(job["host"]) != result["proposal"][0]:
            # A valid action, but on a different host than the one alerting: don't act across hosts.
            result["rationale"] += f"\n[responder] dropped cross-host proposal: {result['proposal']}"
            result["proposal"] = None
    except (ValueError, KeyError, TypeError) as exc:
        result["error"] = f"unusable Claude output ({type(exc).__name__}); rc={record.get('rc')}"
    record["result"] = {**result, "proposal": list(result["proposal"]) if result["proposal"] else None}

    os.makedirs(TRANSCRIPTS, exist_ok=True)
    path = os.path.join(TRANSCRIPTS, f"{job['id']}-{int(started)}.json")
    with open(path, "w") as f:
        json.dump(record, f, indent=1)
    result["transcript"] = path
    return result
