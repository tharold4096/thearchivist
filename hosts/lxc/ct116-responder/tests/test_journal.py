"""journal.py against a local bare repo: queueing, scrubbing, and main moving between pushes."""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NTFY_URL", "http://127.0.0.1:9/x")
os.environ.setdefault("NTFY_TOKEN", "x")
import journal  # noqa: E402

T0 = 1_800_000_000


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


class JournalTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = self.dir.name
        self.bare = os.path.join(d, "remote.git")
        git("init", "-q", "--bare", "-b", "main", self.bare)
        self.other = os.path.join(d, "other")
        git("clone", "-q", self.bare, self.other)
        self._commit_other("README.md", "repo\n", "init")
        journal.REPO_URL = "file://" + self.bare
        journal.CLONE = os.path.join(d, "clone")
        journal.QUEUE = os.path.join(d, "queue")
        journal.flush_async = lambda: None  # tests flush synchronously

    def tearDown(self):
        self.dir.cleanup()

    def _commit_other(self, name, text, msg):
        git("pull", "-q", "--rebase", "origin", "main", cwd=self.other) if git("branch", "-r", cwd=self.other) else None
        with open(os.path.join(self.other, name), "w") as f:
            f.write(text)
        git("add", name, cwd=self.other)
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", msg, cwd=self.other)
        git("push", "-q", "origin", "HEAD:main", cwd=self.other)

    def remote_file(self, rel):
        return git("--git-dir", self.bare, "show", f"main:{rel}")

    def job(self, host="jellyfin"):
        return {"id": "abcdef012345", "host": host, "service": "HTTPS", "created_at": T0}

    def test_records_append_and_queue_clears(self):
        journal.record(self.job(), "diagnosis", "Diagnosis: stopped.")
        journal.record(self.job(), "approved", "Ran restart. Result: ok.")
        journal._flush()
        rel = [l for l in git("--git-dir", self.bare, "ls-tree", "-r", "--name-only", "main").split()
               if l.startswith("journal/")][0]
        text = self.remote_file(rel)
        self.assertIn("# jellyfin / HTTPS", text)
        self.assertLess(text.index("diagnosis"), text.index("approved"))
        self.assertEqual(os.listdir(journal.QUEUE), [])

    def test_main_moving_between_records_does_not_lose_anything(self):
        journal.record(self.job(), "diagnosis", "first")
        journal._flush()
        self._commit_other("MERGED.md", "a PR merge\n", "merge")   # main moves, like PR #4 tonight
        journal.record(self.job(), "approved", "second")
        journal._flush()
        rel = [l for l in git("--git-dir", self.bare, "ls-tree", "-r", "--name-only", "main").split()
               if l.startswith("journal/")][0]
        text = self.remote_file(rel)
        self.assertIn("first", text)
        self.assertIn("second", text)
        self.assertEqual(self.remote_file("MERGED.md"), "a PR merge\n")
        self.assertEqual(os.listdir(journal.QUEUE), [])

    def test_unreachable_remote_keeps_queue(self):
        journal.REPO_URL = "file:///nonexistent/repo.git"
        journal._auth_problem = lambda stderr: None
        journal.record(self.job(), "diagnosis", "kept")
        journal._flush()
        self.assertEqual(len(os.listdir(journal.QUEUE)), 1)

    def test_arr_hosts_never_queued(self):
        journal.record(self.job(host="sonarr"), "diagnosis", "x")
        self.assertFalse(os.path.isdir(journal.QUEUE) and os.listdir(journal.QUEUE))

    def test_secrets_scrubbed_before_queueing(self):
        journal.record(self.job(), "diagnosis", "log had tk_AbCdEf1234567890xyz and password=hunter2")
        journal._flush()
        rel = [l for l in git("--git-dir", self.bare, "ls-tree", "-r", "--name-only", "main").split()
               if l.startswith("journal/")][0]
        text = self.remote_file(rel)
        self.assertNotIn("tk_AbCdEf", text)
        self.assertNotIn("hunter2", text)


if __name__ == "__main__":
    unittest.main()
