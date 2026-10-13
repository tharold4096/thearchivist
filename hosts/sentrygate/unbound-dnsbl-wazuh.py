#!/usr/local/bin/python3
"""
unbound-dnsbl-wazuh - bridge Unbound DNSBL block events into a Wazuh-readable log.

WHY THIS EXISTS
---------------
OPNsense's Unbound DNSBL module does not log blocked queries to syslog. On a
block it calls Logger.log_entry(), which writes a pipe-delimited record to the
named FIFO /var/unbound/data/dns_logger. The only stock consumer is
/usr/local/opnsense/scripts/unbound/logger.py, which writes to a SQLite
database for the Reporting UI - not to any file the Wazuh agent can read.
With no consumer attached, unbound logs "dnsbl_module: no logging backend
found" every 10s and the events are dropped.

This daemon attaches to that FIFO, keeps only genuine blocks, and appends them
as JSON lines. The Wazuh agent reads that file with log_format=json, so every
field is decoded and searchable without a custom decoder.

FIFO WIRE FORMAT (13 pipe-separated fields), from
/usr/local/opnsense/scripts/unbound-dnsbl/lib/log.py and lib/__init__.py:

    uuid|created_at|client|family|type|domain|
    action|source|blocklist|rcode|resolve_time_ms|dnssec_status|ttl

'uuid' is the DNSBL policy id and is non-empty ONLY for blocked queries;
allowed queries traverse the same FIFO with an empty uuid. We emit only the
blocks, which keeps volume proportional to enforcement rather than to total
DNS traffic.

!! CONTENTION WARNING !!
A FIFO delivers each byte to exactly one reader. If OPNsense's own Unbound
"Reporting" backend (logger.py) is enabled while this daemon runs, the two
processes SPLIT the stream and both datasets become silently incomplete.
Run one or the other, never both. This daemon refuses to start if logger.py
is already running.
"""
import json
import os
import signal
import subprocess
import sys
import time

FIFO = '/var/unbound/data/dns_logger'
OUT = '/var/log/unbound-dnsbl/blocks.log'
HOSTNAME = os.uname()[1]

FIELDS = [
    'policy_id', 'created_at', 'srcip', 'family', 'qtype', 'domain',
    'action', 'source', 'blocklist', 'rcode', 'resolve_time_ms',
    'dnssec_status', 'ttl',
]

# The module writes these as bare integers. Map them to readable strings so the
# dashboard is searchable by name (action:block) rather than by magic number.
# Values from /usr/local/opnsense/scripts/unbound-dnsbl/dnsbl_module.py.
ACTION_MAP = {'0': 'pass', '1': 'block', '2': 'drop'}
SOURCE_MAP = {'0': 'recursion', '1': 'local', '2': 'localdata', '3': 'cache'}
RCODE_MAP = {'0': 'NOERROR', '3': 'NXDOMAIN'}

_running = True


def _stop(*_a):
    """Terminate on SIGTERM/SIGINT.

    This MUST raise. The main loop spends nearly all its time blocked in
    open() or read() on the FIFO, and under PEP 475 a handler that merely
    sets a flag lets Python retry the interrupted syscall - so the process
    would ignore SIGTERM until the next DNSBL block arrived, which may be
    hours. 'service ... stop' would report success while the old instance
    kept running, and a subsequent start would leave two readers splitting
    the FIFO between them.
    """
    global _running
    _running = False
    raise SystemExit(0)


def logger_py_running():
    """Refuse to fight OPNsense's own FIFO consumer - see contention warning."""
    try:
        out = subprocess.run(['/bin/ps', '-axww', '-o', 'command'],
                             capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return False
    return any('unbound/logger.py' in ln for ln in out.splitlines())


def emit(fh, rec):
    fh.write(json.dumps(rec, separators=(',', ':')) + '\n')
    fh.flush()


def parse(line):
    parts = line.rstrip('\n').split('|')
    if len(parts) != len(FIELDS):
        return None
    rec = dict(zip(FIELDS, parts))
    # Empty policy_id means the query was NOT blocked - drop it.
    if not rec['policy_id']:
        return None
    for k in ('created_at', 'resolve_time_ms', 'ttl'):
        try:
            rec[k] = int(rec[k]) if rec[k] != '' else None
        except ValueError:
            rec[k] = None
    rec['action'] = ACTION_MAP.get(rec['action'], rec['action'] or 'block')
    rec['source'] = SOURCE_MAP.get(rec['source'], rec['source'])
    rec['rcode'] = RCODE_MAP.get(rec['rcode'], rec['rcode'])
    # Trailing dot is how unbound represents the FQDN root; strip for searchability.
    rec['domain'] = rec['domain'].rstrip('.')
    rec['integration'] = 'unbound-dnsbl'
    rec['hostname'] = HOSTNAME
    rec['timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%S%z',
                                     time.localtime(rec['created_at'] or time.time()))
    return rec


def main():
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    if logger_py_running():
        sys.stderr.write('refusing to start: OPNsense unbound logger.py holds the FIFO\n')
        return 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    while _running:
        if not os.path.exists(FIFO):
            # unbound recreates the FIFO on restart; wait for it rather than dying.
            time.sleep(5)
            continue
        try:
            # Blocking open: returns once unbound opens the write end.
            with open(FIFO, 'r') as fifo, open(OUT, 'a') as out:
                for line in fifo:
                    if not _running:
                        break
                    rec = parse(line)
                    if rec:
                        emit(out, rec)
            # EOF: unbound closed its end (restart/reload). Loop and reopen.
        except Exception as e:
            sys.stderr.write('bridge error: %s\n' % e)
            time.sleep(5)
    return 0


if __name__ == '__main__':
    sys.exit(main())
