"""Tests for grants.py and the store auto-approve path."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import grants  # noqa: E402
import store  # noqa: E402
from registry import Registry  # noqa: E402

T0 = 1_800_000_000
REG = Registry({
    "hosts": {
        "jellyfin": {"checkmk_name": "jellyfin", "ip": "x", "unit": "jellyfin.service",
                     "read_verbs": ["status"], "write_verbs": ["restart"]},
        "ntfy": {"checkmk_name": "ntfy", "ip": "x", "unit": "ntfy.service",
                 "read_verbs": ["status"], "write_verbs": ["restart"]},
        "flagged": {"checkmk_name": "flagged", "ip": "x", "unit": "x.service",
                    "read_verbs": [], "write_verbs": ["restart"], "protected": True},
    },
    "protected": {"checkmk_names": ["ntfy"], "units": []},
})
TUPLE = ("jellyfin", "restart", "jellyfin.service")


class GrantsTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.db = store.connect(os.path.join(self.dir.name, "r.db"))
        grants.ensure_schema(self.db)

    def tearDown(self):
        self.db.close()
        self.dir.cleanup()

    def test_no_grant_until_recorded(self):
        self.assertEqual(grants.check_auto(self.db, REG, *TUPLE, T0), (None, grants.NO_GRANT))
        gid = grants.record(self.db, REG, *TUPLE, "job1", T0)
        self.assertEqual(grants.check_auto(self.db, REG, *TUPLE, T0 + 1), (gid, "ok"))

    def test_grant_is_exact(self):
        grants.record(self.db, REG, *TUPLE, "job1", T0)
        self.assertEqual(grants.check_auto(self.db, REG, "jellyfin", "restart", "other.service", T0)[1],
                         grants.NO_GRANT)

    def test_protected_never_recorded_or_auto(self):
        self.assertIsNone(grants.record(self.db, REG, "ntfy", "restart", "ntfy.service", "j", T0))
        self.assertIsNone(grants.record(self.db, REG, "flagged", "restart", "x.service", "j", T0))
        self.assertIsNone(grants.record(self.db, REG, "unknown", "restart", "x.service", "j", T0))
        # Even a hand-crafted row doesn't make a protected target auto-run.
        self.db.execute("INSERT INTO grants (id, host, verb, unit, created_at, approved_job)"
                        " VALUES ('aaaaaaaaaaaa', 'ntfy', 'restart', 'ntfy.service', 0, 'x')")
        self.assertEqual(grants.check_auto(self.db, REG, "ntfy", "restart", "ntfy.service", T0),
                         (None, grants.PROTECTED))

    def test_two_auto_runs_per_24h_then_manual(self):
        gid = grants.record(self.db, REG, *TUPLE, "job1", T0)
        for i in range(2):
            run = grants.start_auto_run(self.db, gid, f"j{i}", T0 + i)
            grants.finish_auto_run(self.db, run, gid, True, T0 + i)
        self.assertEqual(grants.check_auto(self.db, REG, *TUPLE, T0 + 10)[1], grants.TUPLE_LIMIT)
        self.assertEqual(grants.check_auto(self.db, REG, *TUPLE, T0 + 86401)[1], "ok")

    def test_failed_verify_demotes(self):
        gid = grants.record(self.db, REG, *TUPLE, "job1", T0)
        run = grants.start_auto_run(self.db, gid, "j", T0)
        grants.finish_auto_run(self.db, run, gid, False, T0)
        self.assertEqual(grants.check_auto(self.db, REG, *TUPLE, T0 + 1)[1], grants.NO_GRANT)

    def test_revoke_once(self):
        gid = grants.record(self.db, REG, *TUPLE, "job1", T0)
        tok = grants.revoke_link(self.db, gid)
        self.assertEqual(grants.revoke(self.db, gid, "x" * 32, T0), "invalid")
        self.assertEqual(grants.revoke(self.db, "000000000000", tok, T0), "invalid")
        self.assertEqual(grants.revoke(self.db, gid, tok, T0), "revoked")
        self.assertEqual(grants.revoke(self.db, gid, tok, T0), "already_revoked")
        self.assertEqual(grants.check_auto(self.db, REG, *TUPLE, T0)[1], grants.NO_GRANT)

    def test_auto_approve_only_from_open_and_then_executes_once(self):
        job, _ = store.intake_alert(self.db, "jellyfin", "HTTP", "PROBLEM", "CRIT", "", T0, 3600)
        self.assertTrue(store.auto_approve(self.db, job, "restart", "jellyfin.service", T0))
        self.assertFalse(store.auto_approve(self.db, job, "restart", "jellyfin.service", T0))
        self.assertTrue(store.start_execution(self.db, job, T0))
        self.assertFalse(store.start_execution(self.db, job, T0))
        self.assertEqual(store.interrupted(self.db, T0 + 5), [job])

    def test_validate_proposal(self):
        self.assertEqual(REG.validate_proposal({"host": "jellyfin", "verb": "restart"}), TUPLE)
        self.assertIsNone(REG.validate_proposal({"host": "jellyfin", "verb": "rm"}))
        self.assertIsNone(REG.validate_proposal({"host": "thearchivist", "verb": "restart"}))
        self.assertIsNone(REG.validate_proposal("restart jellyfin"))
        self.assertIsNone(REG.validate_proposal(None))


if __name__ == "__main__":
    unittest.main()
