from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_post.py"
CONFIG = ROOT / "config" / "posts.json"


class PreparePostTests(unittest.TestCase):
    def test_all_posts_are_valid_and_under_limit(self) -> None:
        posts = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(posts), 1)
        for post in posts:
            self.assertLessEqual(len(post["text"]), 280)
            self.assertTrue((ROOT / post["image"]).is_file())
            self.assertIn("https://www.epic-creation.com/", post["text"])

    def test_deterministic_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--date",
                    "2026-07-24",
                    "--index",
                    "3",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["date"], "2026-07-24")
            self.assertEqual(metadata["post_id"], "vehicle-api")
            self.assertTrue((output / "post.txt").is_file())
            self.assertTrue((output / "issue_body.md").is_file())
            self.assertTrue((output / metadata["image"]).is_file())


if __name__ == "__main__":
    unittest.main()
