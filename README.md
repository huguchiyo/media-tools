# Tools

写真・動画のインポート後から YouTube アップロードまでを一連の流れで扱うためのツール群です。

## ワークフロー概要（4ステップ）

| # | 内容 | 担当 | 記録先 |
|---|------|------|--------|
| 1 | **camera** の動画をリネームして **movie** に移動 | VideoMoveTools | — |
| 2 | どのフォルダにどの動画が移動したかを記録し、結果を表示 | VideoMoveTools | `VideoMoveTools/moved_videos_log.json`（確認用: `moved_videos_log.md`） |
| 3 | movie の動画のうち未アップロードを確認し結果を表示。該当年を YouTube にアップロード | youtube | — |
| 4 | アップロード結果を記録 | youtube | `youtube/data/upload_runs.json`（確認用: `upload_runs.md`）および `uploaded_from_youtube.txt` |

- **1・2**: [VideoMoveTools](VideoMoveTools/README.md) のリネーム規則に従い、`camera`（または指定ソース）の動画を `movie/YYYY/` に移動し、その結果を `moved_videos_log.json` に追記します。実行後は**移動結果（年ごとの一覧）を表示**します。
- **3**: **movie フォルダ**をスキャンし、`youtube/data/uploaded_from_youtube.txt` に載っていない動画を**未アップロードとして一覧表示**します。該当する年のフォルダを YouTube にアップロードするか確認してから本番実行します。
- **4**: 各アップロード実行ごとに `youtube_upload.py` が成功・スキップ・失敗件数を `youtube/data/upload_runs.json` に追記し、アップロード済みタイトルは `uploaded_from_youtube.txt` に追記します。

## 一括実行（ワークフロースクリプト）

`workflow.py` で「移動」と「移動ログに基づくアップロード」をまとめて実行できます。

```bash
# カレントを Tools にして実行
cd G:\Users\chiyo\Pictures\Tools

# ドライラン（移動もアップロードも実際には行わない）
python workflow.py --move --upload-from-move-log --dry-run

# 移動のみ実行（確認プロンプトなし）
python workflow.py --move

# movie 内の未アップロード動画を表示し、該当年をアップロード（確認プロンプト → 本番）
python workflow.py --upload-from-move-log

# 確認をスキップしてそのままアップロード（非対話・自動実行用）
python workflow.py --upload-from-move-log --yes

# 移動 → アップロードを続けて実行
python workflow.py --move --upload-from-move-log

# 年を指定してアップロード（movie スキャンではなく指定年のみ）
python workflow.py --years 2024 2025
```

- `--move`: ステップ 1・2 を実行（VideoMoveTools の移動スクリプトを実行）。
- `--upload-from-move-log`: ステップ 3・4 を実行。**movie フォルダ**をスキャンし、`uploaded_from_youtube.txt` に無い動画を**未アップロードとして表示**してから、該当年の `movie/YYYY` をアップロード。結果は `youtube_upload.py` により `upload_runs.json` に記録。
- `--movie-dir`: movie フォルダのパス（未アップロード判定で参照。既定: `G:/Users/chiyo/Pictures/movie`）。
- `--years 2024 2025`: アップロードする年を直接指定（movie スキャンは行わず、指定した年のみアップロード）。
- `--dry-run`: 移動・アップロードともに実際には行いません。
- `--no-fetch-list`: アップロード時に YouTube API で一覧を取得せず、ローカルの `uploaded_from_youtube.txt` のみでスキップ判定します（2年目以降は自動でローカルのみ使用）。

## 個別ツール

- **[VideoMoveTools](VideoMoveTools/README.md)**  
  - 動画のリネーム規則・移動先・重複判定・`moved_videos_log.json` の形式はここに記載されています。
- **[youtube](youtube/README.md)**  
  - アップロードの詳細オプション、認証、`uploaded_from_youtube.txt` / `upload_runs.json` の扱いはここを参照してください。
- **PhotoMergeTools**  
  - 写真のマージ・重複分析用。動画ワークフローとは独立しています。

## フォルダ構成の想定

- **camera**: インポートした写真・動画が入るフォルダ（日付フォルダや年フォルダ）。
- **movie**: 動画のみリネーム後に年ごとに格納するフォルダ（`movie/2024/`, `movie/2025/` など）。

移動先ベースは VideoMoveTools のデフォルト（`movie`）または `--target` で指定。アップロード時は `--movie-dir`（既定で同じ movie パス）でスキャンし、未アップロード判定に `uploaded_from_youtube.txt` を使います。
