"""Tests for store.py. Run from configs/responder: python3 -m unittest discover -s tests -v"""
import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import store  # noqa: E402

T0 = 1_800_000_000
WINDOW = 3600
TTL = 1800


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "responder.db")
        self.db = store.connect(self.path)

    def tearDown(self):
        self.db.close()
        self.dir.cleanup()

    def alert(self, now=T0, host="jellyfin", service="Jellyfin HTTP", ntype="PROBLEM"):
        return store.intake_alert(self.db, host, service, ntype, "CRIT", "connection refused", now, WINDOW)

    def pending_job(self, now=T0):
        job_id, _ = self.alert(now)
        token = store.propose(self.db, job_id, "restart", "jellyfin.service", now, TTL)
        return job_id, token

    # --- dedupe: one problem, one session ---

    def test_repeat_alert_attaches_to_live_job(self):
        a, new_a = self.alert()
        b, new_b = self.alert(T0 + 60)
        self.assertTrue(new_a)
        self.assertFalse(new_b)
        self.assertEqual(a, b)
        n = self.db.execute("SELECT COUNT(*) FROM alerts WHERE job_id = ?", (a,)).fetchone()[0]
        self.assertEqual(n, 2)

    def test_different_service_is_a_different_job(self):
        a, _ = self.alert()
        b, new_b = self.alert(service="Jellyfin disk")
        self.assertTrue(new_b)
        self.assertNotEqual(a, b)

    def test_after_recovery_a_new_problem_is_a_new_job(self):
        a, _ = self.alert()
        self.assertEqual(store.recover(self.db, "jellyfin", "Jellyfin HTTP", T0 + 60), [a])
        b, new_b = self.alert(T0 + 120)
        self.assertTrue(new_b)
        self.assertNotEqual(a, b)

    def test_denied_problem_refiring_inside_window_attaches(self):
        job_id, token = self.pending_job()
        store.claim(self.db, job_id, token, "denied", T0 + 10)
        store.close(self.db, job_id, "denied", T0 + 10)
        again, new = self.alert(T0 + WINDOW - 1)
        self.assertFalse(new)
        self.assertEqual(again, job_id)
        later, new_later = self.alert(T0 + 10 + WINDOW + 1)
        self.assertTrue(new_later)

    def test_concurrent_alerts_open_one_job(self):
        results = self._race(20, lambda db: store.intake_alert(
            db, "jellyfin", "Jellyfin HTTP", "PROBLEM", "CRIT", "x", T0, WINDOW))
        self.assertEqual(sum(1 for _, new in results if new), 1)
        self.assertEqual(len({job for job, _ in results}), 1)

    # --- proposals and the double-tap guard ---

    def test_token_is_not_stored_in_plaintext(self):
        job_id, token = self.pending_job()
        dump = "\n".join(self.db.iterdump())
        self.assertNotIn(token, dump)

    def test_propose_only_once(self):
        job_id, _ = self.pending_job()
        self.assertIsNone(store.propose(self.db, job_id, "restart", "jellyfin.service", T0, TTL))

    def test_wrong_token_is_invalid_and_changes_nothing(self):
        job_id, _ = self.pending_job()
        self.assertEqual(store.claim(self.db, job_id, "nope", "approved", T0 + 1), (store.INVALID, None))
        self.assertEqual(store.claim(self.db, "nojob", "nope", "approved", T0 + 1), (store.INVALID, None))
        self.assertEqual(store.get(self.db, job_id)["state"], "pending")

    def test_second_tap_is_already_handled(self):
        job_id, token = self.pending_job()
        self.assertEqual(store.claim(self.db, job_id, token, "approved", T0 + 1), (store.CLAIMED, "approved"))
        self.assertEqual(store.claim(self.db, job_id, token, "approved", T0 + 2),
                         (store.ALREADY_HANDLED, "approved"))
        # Deny after Approve (the other dead button) doesn't flip it either.
        self.assertEqual(store.claim(self.db, job_id, token, "denied", T0 + 3),
                         (store.ALREADY_HANDLED, "approved"))

    def test_tap_after_expiry_is_refused(self):
        job_id, token = self.pending_job()
        self.assertEqual(store.claim(self.db, job_id, token, "approved", T0 + TTL), (store.EXPIRED, "expired"))
        self.assertEqual(store.get(self.db, job_id)["state"], "expired")
        self.assertFalse(store.start_execution(self.db, job_id, T0 + TTL))

    def test_simultaneous_taps_exactly_one_wins(self):
        job_id, token = self.pending_job()
        results = self._race(20, lambda db: store.claim(db, job_id, token, "approved", T0 + 1))
        self.assertEqual([r for r, _ in results].count(store.CLAIMED), 1)
        self.assertEqual([r for r, _ in results].count(store.ALREADY_HANDLED), 19)

    def test_simultaneous_approve_and_deny_exactly_one_wins(self):
        job_id, token = self.pending_job()
        decisions = ["approved", "denied"] * 10
        results = self._race(20, lambda db, i=iter(decisions), lock=threading.Lock():
                             store.claim(db, job_id, token, self._next(i, lock), T0 + 1))
        self.assertEqual([r for r, _ in results].count(store.CLAIMED), 1)

    # --- execution guard ---

    def test_execution_starts_once(self):
        job_id, token = self.pending_job()
        store.claim(self.db, job_id, token, "approved", T0 + 1)
        results = self._race(20, lambda db: store.start_execution(db, job_id, T0 + 2))
        self.assertEqual(results.count(True), 1)

    def test_denied_job_never_executes(self):
        job_id, token = self.pending_job()
        store.claim(self.db, job_id, token, "denied", T0 + 1)
        self.assertFalse(store.start_execution(self.db, job_id, T0 + 2))

    def test_recovery_before_execution_cancels_it(self):
        job_id, token = self.pending_job()
        store.claim(self.db, job_id, token, "approved", T0 + 1)
        store.recover(self.db, "jellyfin", "Jellyfin HTTP", T0 + 2)
        self.assertFalse(store.start_execution(self.db, job_id, T0 + 3))
        self.assertEqual(store.get(self.db, job_id)["close_reason"], "recovered")

    def test_recovery_leaves_running_execution_alone(self):
        job_id, token = self.pending_job()
        store.claim(self.db, job_id, token, "approved", T0 + 1)
        store.start_execution(self.db, job_id, T0 + 2)
        self.assertEqual(store.recover(self.db, "jellyfin", "Jellyfin HTTP", T0 + 3), [])
        self.assertEqual(store.get(self.db, job_id)["state"], "executing")

    def test_expire_due(self):
        job_id, _ = self.pending_job()
        self.assertEqual(store.expire_due(self.db, T0 + TTL - 1), [])
        self.assertEqual(store.expire_due(self.db, T0 + TTL), [job_id])
        self.assertEqual(store.expire_due(self.db, T0 + TTL + 1), [])

    def test_close_is_idempotent(self):
        job_id, _ = self.alert()
        self.assertTrue(store.close(self.db, job_id, "done", T0 + 1))
        self.assertFalse(store.close(self.db, job_id, "done", T0 + 2))

    # --- helpers ---

    @staticmethod
    def _next(it, lock):
        with lock:
            return next(it)

    def _race(self, n, fn):
        """Run fn(conn) in n threads, each with its own connection, released together."""
        barrier = threading.Barrier(n)
        results = [None] * n
        errors = []

        def worker(i):
            db = store.connect(self.path)
            try:
                barrier.wait()
                results[i] = fn(db)
            except Exception as exc:  # surfaced below
                errors.append(exc)
            finally:
                db.close()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        return results


if __name__ == "__main__":
    unittest.main()
