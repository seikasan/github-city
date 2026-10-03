"""Exercise first publish, subsequent update and no-op against a local bare remote."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name != "nt" and shutil.which("git") and shutil.which("bash"), "Needs git and bash on Unix")
class PublishTests(unittest.TestCase):
    def test_publish_keeps_main_unchanged_and_preserves_asset_history(self):
        script = Path(__file__).resolve().parents[1] / "publish_city.sh"
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            repo, remote = base / "source", base / "remote.git"
            repo.mkdir()
            env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
            def run(*args, cwd=repo):
                result = subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=True, text=True)
                return result.stdout.strip()
            run("git", "init", "--bare", str(remote), cwd=base)
            run("git", "init", "-b", "main")
            (repo / "README.md").write_text("original profile")
            run("git", "add", ".")
            run("git", "commit", "-m", "initial")
            original_head = run("git", "rev-parse", "HEAD")
            run("git", "remote", "add", "origin", str(remote))
            run("git", "push", "origin", "main")
            city = base / "city.svg"
            city.write_text('<svg xmlns="http://www.w3.org/2000/svg"><title>one</title></svg>')
            run("bash", str(script), str(city))
            asset_head = run("git", "--git-dir", str(remote), "rev-parse", "city-art")
            self.assertEqual(run("git", "--git-dir", str(remote), "ls-tree", "--name-only", "city-art"), "city.svg")
            self.assertEqual(run("git", "--git-dir", str(remote), "rev-list", "--count", "city-art"), "1")
            self.assertEqual(run("git", "rev-parse", "HEAD"), original_head)
            self.assertEqual(run("git", "--git-dir", str(remote), "rev-parse", "main"), original_head)
            run("bash", str(script), str(city))
            self.assertEqual(run("git", "--git-dir", str(remote), "rev-parse", "city-art"), asset_head)
            city.write_text('<svg xmlns="http://www.w3.org/2000/svg"><title>two</title></svg>')
            run("bash", str(script), str(city))
            self.assertEqual(run("git", "--git-dir", str(remote), "rev-list", "--count", "city-art"), "2")
            self.assertEqual(run("git", "--git-dir", str(remote), "rev-parse", "main"), original_head)
            self.assertEqual((repo / "README.md").read_text(), "original profile")


if __name__ == "__main__":
    unittest.main()
