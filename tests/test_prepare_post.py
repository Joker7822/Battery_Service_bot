from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_post.py"
MATERIALIZE = ROOT / "scripts" / "materialize_images.py"
CONFIG = ROOT / "config" / "posts.json"


class PreparePostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        result = subprocess.run(
            ["python3", str(MATERIALIZE)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

    def test_all_four_promotional_images_are_materialized(self) -> None:
        for index in range(1, 5):
            image = ROOT / "assets" / f"post_{index:02d}.jpg"
            self.assertTrue(image.is_file(), image)
            data = image.read_bytes()
            self.assertTrue(data.startswith(b"\xff\xd8"), image)
            self.assertTrue(data.endswith(b"\xff\xd9"), image)

    def test_all_posts_are_valid_and_under_limit(self) -> None:
        posts = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(posts), 1)
        self.assertEqual(
            {post["image"] for post in posts},
            {
                "assets/post_01.jpg",
                "assets/post_02.jpg",
                "assets/post_03.jpg",
                "assets/post_04.jpg",
            },
        )
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
            self.assertEqual(metadata["image_source"], "assets/post_02.jpg")
            self.assertTrue((output / "post.txt").is_file())
            self.assertTrue((output / "issue_body.md").is_file())
            self.assertTrue((output / metadata["image"]).is_file())


if __name__ == "__main__":
    unittest.main()
