# Battery Service Epic X投稿準備Bot

X APIを使わず、GitHub Actionsで毎日の投稿文と宣材画像を自動準備する半自動Botです。

## 動作

毎日 **9:17（日本時間）** に次の処理を実行します。

1. 8種類の投稿文から日付に応じて1件を選択
2. 対応する宣材画像を選択
3. `post.txt`・画像・メタデータをActions Artifactへ保存
4. GitHub Issueを作成して `Joker7822` に割り当て
5. GitHub Mobileアプリへ通知
6. Issueから投稿文をコピーし、画像を保存してXへ手動投稿

Xへの最終投稿操作は人が行うため、X APIキーは不要です。

## 初回設定

### 1. GitHub Actionsを有効化

リポジトリの **Actions** タブを開き、ワークフローを有効にします。

### 2. GitHub Mobileの通知を有効化

スマートフォンへGitHub Mobileをインストールし、以下の通知を有効にします。

- GitHub Mobileのプッシュ通知
- `Joker7822/Battery_Service_bot` のIssue通知
- 自分が割り当てられたIssueの通知

### 3. 手動テスト

1. **Actions** を開く
2. **Prepare Daily X Post** を選択
3. **Run workflow** を押す
4. `create_issue` を有効にしたまま実行
5. Issueとスマートフォン通知を確認

## 自動実行時刻

```yaml
schedule:
  - cron: "17 9 * * *"
    timezone: "Asia/Tokyo"
```

毎日9時17分・日本時間に実行します。毎時0分付近の混雑を避けるため、17分に設定しています。

## 投稿内容の編集

`config/posts.json`を編集します。

必須項目:

- `id`: 投稿を識別する一意のID
- `text`: X投稿文（280文字以内）
- `image`: リポジトリ内の画像パス
- `alt`: Issue内の画像説明

投稿文は日付から決定されるため、状態ファイルを保存しなくても順番に切り替わります。

## 宣材画像

`assets/`に3種類のJPEG画像を保存しています。

- `post_01.jpg`
- `post_02.jpg`
- `post_03.jpg`

投稿ごとに使用画像は`config/posts.json`で指定します。

## 生成物

Actions Artifactには次が含まれます。

```text
post.txt
issue_body.md
metadata.json
YYYY-MM-DD_<post-id>.jpg
```

保存期間は30日です。

## 重複通知防止

同じ日・同じ投稿IDのIssueがすでに存在する場合、新しいIssueは作成しません。ワークフローを再実行しても通知が重複しない構成です。

## ローカル確認

```bash
python -m unittest discover -s tests -v
python scripts/prepare_post.py --date 2026-07-24 --index 3
```

生成結果は`output/`へ出力されます。

## サービスページ

https://www.epic-creation.com/Epic/Epic-Creation/Battery_Service/index.php
