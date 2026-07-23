#!/usr/bin/env python3
"""Prepare a daily X post package without using the X API."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "posts.json"
DEFAULT_OUTPUT = REPO_ROOT / "output"
SITE_URL = "https://www.epic-creation.com/Epic/Epic-Creation/Battery_Service/index.php"
MAX_TEXT_LENGTH = 280


@dataclass(frozen=True)
class Post:
    post_id: str
    text: str
    image: Path
    image_repo_path: str
    alt: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--date", dest="target_date", help="YYYY-MM-DD (default: today in Asia/Tokyo)")
    parser.add_argument("--index", type=int, help="1-based post index. Omit for date-based rotation.")
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY", "Joker7822/Battery_Service_bot"))
    parser.add_argument("--branch", default=os.getenv("GITHUB_REF_NAME", "main"))
    return parser.parse_args()


def load_posts(config_path: Path) -> list[Post]:
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"投稿設定が見つかりません: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"投稿設定JSONが不正です: {exc}") from exc

    if not isinstance(raw, list) or not raw:
        raise RuntimeError("投稿設定には1件以上の投稿が必要です。")

    posts: list[Post] = []
    seen_ids: set[str] = set()
    for position, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"投稿{position}がオブジェクトではありません。")

        post_id = str(item.get("id", "")).strip()
        text = str(item.get("text", "")).strip()
        image_repo_path = str(item.get("image", "")).strip().replace("\\", "/")
        alt = str(item.get("alt", "")).strip()

        if not post_id or post_id in seen_ids:
            raise RuntimeError(f"投稿{position}のidが空、または重複しています: {post_id!r}")
        if not text:
            raise RuntimeError(f"投稿{position}のtextが空です。")
        if len(text) > MAX_TEXT_LENGTH:
            raise RuntimeError(
                f"投稿{position} ({post_id}) が{MAX_TEXT_LENGTH}文字を超えています: {len(text)}文字"
            )
        if SITE_URL not in text:
            raise RuntimeError(f"投稿{position} ({post_id}) にサービスURLがありません。")
        if not image_repo_path:
            raise RuntimeError(f"投稿{position} ({post_id}) のimageが空です。")

        image = REPO_ROOT / image_repo_path
        if not image.is_file():
            raise RuntimeError(f"投稿{position} ({post_id}) の画像が見つかりません: {image}")
        if image.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise RuntimeError(f"未対応の画像形式です: {image.suffix}")

        seen_ids.add(post_id)
        posts.append(Post(post_id, text, image, image_repo_path, alt))

    return posts


def resolve_date(value: str | None) -> date:
    if value:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise RuntimeError("--date は YYYY-MM-DD 形式で指定してください。") from exc
    return datetime.now(ZoneInfo("Asia/Tokyo")).date()


def select_post(posts: list[Post], target_date: date, requested_index: int | None) -> tuple[int, Post]:
    if requested_index is not None:
        if requested_index < 1 or requested_index > len(posts):
            raise RuntimeError(f"--index は1〜{len(posts)}で指定してください。")
        index = requested_index - 1
    else:
        index = (target_date.toordinal() - 1) % len(posts)
    return index, posts[index]


def write_github_output(values: dict[str, str]) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            if "\n" in value:
                raise RuntimeError(f"GitHub output {key} に改行は使用できません。")
            handle.write(f"{key}={value}\n")


def build_issue_body(
    *,
    post: Post,
    index: int,
    count: int,
    target_date: date,
    repository: str,
    branch: str,
    image_name: str,
) -> str:
    raw_image_url = (
        f"https://raw.githubusercontent.com/{repository}/{quote(branch, safe='')}/{post.image_repo_path}"
    )
    intent_url = f"https://x.com/intent/post?text={quote(post.text, safe='')}"

    return f"""## 本日のX投稿候補

**対象日:** {target_date.isoformat()}（日本時間）  
**ローテーション:** {index + 1}/{count}  
**投稿ID:** `{post.post_id}`  
**文字数（単純カウント）:** {len(post.text)}/{MAX_TEXT_LENGTH}

### 投稿文

```text
{post.text}
```

### 投稿画像

![{post.alt}]({raw_image_url})

- [画像を原寸で開く]({raw_image_url})
- Actionsの実行結果から `{image_name}` を含む投稿セットもダウンロードできます。

### 手動投稿

1. 上の投稿文をコピーします。
2. 画像をスマートフォンへ保存します。
3. [Xの投稿画面を開く]({intent_url})をタップします。
4. 画像を添付し、内容を確認してから投稿します。
5. 投稿完了後、このIssueを閉じます。

> X APIは使用していません。投稿ボタンを押す最終操作は手動です。
"""


def prepare_package(args: argparse.Namespace) -> dict[str, str]:
    posts = load_posts(args.config)
    target_date = resolve_date(args.target_date)
    index, post = select_post(posts, target_date, args.index)

    output_dir = args.output.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    image_name = f"{target_date.isoformat()}_{post.post_id}{post.image.suffix.lower()}"
    output_image = output_dir / image_name
    shutil.copy2(post.image, output_image)

    (output_dir / "post.txt").write_text(post.text + "\n", encoding="utf-8")

    issue_title = f"[X投稿準備] {target_date.isoformat()} - {post.post_id}"
    issue_body = build_issue_body(
        post=post,
        index=index,
        count=len(posts),
        target_date=target_date,
        repository=args.repository,
        branch=args.branch,
        image_name=image_name,
    )
    (output_dir / "issue_body.md").write_text(issue_body, encoding="utf-8")

    metadata = {
        "date": target_date.isoformat(),
        "index": index + 1,
        "post_count": len(posts),
        "post_id": post.post_id,
        "character_count": len(post.text),
        "image": image_name,
        "image_source": post.image_repo_path,
        "issue_title": issue_title,
        "repository": args.repository,
        "branch": args.branch,
        "generated_at": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds"),
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    values = {
        "date": target_date.isoformat(),
        "post_id": post.post_id,
        "post_index": str(index + 1),
        "issue_title": issue_title,
        "image_name": image_name,
        "artifact_name": f"x-post-{target_date.isoformat()}-{post.post_id}",
    }
    write_github_output(values)
    return values


def main() -> int:
    try:
        values = prepare_package(parse_args())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(values, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
