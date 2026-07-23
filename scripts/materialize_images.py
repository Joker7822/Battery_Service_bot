#!/usr/bin/env python3
"""Decode the repository's promotional-image sources into JPEG files."""

from __future__ import annotations

import base64
import binascii
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENCODED_DIR = ROOT / "assets" / "encoded"
ASSETS_DIR = ROOT / "assets"
IMAGE_COUNT = 4


def materialize_images() -> list[Path]:
    """Create assets/post_01.jpg through assets/post_04.jpg."""
    outputs: list[Path] = []

    for index in range(1, IMAGE_COUNT + 1):
        stem = f"post_{index:02d}"
        parts = sorted(ENCODED_DIR.glob(f"{stem}.b64.part*"))
        if not parts:
            raise RuntimeError(f"Encoded image parts not found: {stem}")

        encoded = "".join(
            part.read_text(encoding="ascii").strip() for part in parts
        )
        try:
            image_data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise RuntimeError(f"Invalid Base64 image source: {stem}") from exc

        if not image_data.startswith(b"\xff\xd8") or not image_data.endswith(b"\xff\xd9"):
            raise RuntimeError(f"Decoded data is not a complete JPEG: {stem}")

        output = ASSETS_DIR / f"{stem}.jpg"
        output.write_bytes(image_data)
        outputs.append(output)
        print(f"Materialized {output.relative_to(ROOT)} ({len(image_data)} bytes)")

    return outputs


if __name__ == "__main__":
    materialize_images()
