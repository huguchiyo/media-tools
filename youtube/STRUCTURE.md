# YouTube API ツール ディレクトリ構造

## ディレクトリ構成

```
Tools/youtube/
├── youtube_upload.py          # メインスクリプト（動画アップロード）
├── youtube_list.py            # 後方互換性のための再エクスポート
├── config.json                 # 設定ファイル
├── config.json.example         # 設定ファイルの例
├── client_secrets.json         # OAuth認証情報
├── README.md                   # メインドキュメント
├── STRUCTURE.md                # ディレクトリ構造ドキュメント
│
├── utils/                      # ライブラリ・ユーティリティ
│   ├── paths.py                # プロジェクト共通パス（data/, logs/, uploaded_from_youtube.txt）
│   ├── auth.py                 # 認証（OAuth 2.0）
│   ├── upload.py               # アップロード処理
│   ├── file_utils.py           # ファイル処理（ファイル名・動画判定）
│   ├── playlist.py             # プレイリスト操作
│   ├── youtube_list.py         # YouTube API リスト操作
│   ├── check_playlist_membership.py  # プレイリストメンバーシップ確認
│   ├── check_unuploaded_videos.py    # 未アップロード動画確認
│   ├── check_should_upload.py        # アップロードすべき動画確認
│   └── delete_video.py               # 動画削除
│
├── tests/                      # テストスクリプト
│   └── test_api.py
│
├── data/                       # データファイル
│   ├── uploaded_from_youtube.txt  # アップロード済み一覧（スキップ判定・成功時に追記）
│   ├── unuploaded_videos.json  # 未アップロード動画リスト（check_unuploaded_videos 等）
│   └── playlist_additions_log.json  # プレイリスト追加ログ
│
├── logs/                       # ログファイル
│   └── *.log
│
└── docs/                       # ドキュメント
    ├── IMPROVEMENTS.md
    └── youtube_list_improvements.md
```

## 使用方法

### メインスクリプトの実行

```bash
cd Tools/youtube
python youtube_upload.py
```

### ユーティリティスクリプトの実行

```bash
cd Tools/youtube
python utils/check_unuploaded_videos.py
python utils/check_playlist_membership.py --fix
```

## インポートパス

### リファクタリング後のモジュール構造

- `youtube_upload.py` からユーティリティをインポートする場合:
  ```python
  from utils import auth
  from utils import file_utils
  from utils import paths
  from utils import playlist
  from utils import upload
  from utils import youtube_list
  ```

- 後方互換性のため、親ディレクトリからも`youtube_list`をインポート可能:
  ```python
  import youtube_list  # utils/youtube_list.pyを再エクスポート
  ```

## 設定・データ

- **スキップ判定**: タイトル一致のみ（`data/uploaded_from_youtube.txt` を参照・追記）。
- `--no-fetch-list`: 起動時に API で一覧取得せず、ローカルの `uploaded_from_youtube.txt` のみ参照（短時間で開始可能）。
- ログは `logs/` に出力。

## モジュールの役割

### コアモジュール（utils/）
- `paths.py`: プロジェクト共通パス（`DATA_DIR`, `UPLOADED_FROM_YOUTUBE_PATH`, `LOGS_DIR`）
- `auth.py`: OAuth 2.0 認証
- `upload.py`: 動画アップロード（リジューム対応）
- `file_utils.py`: ファイル名・動画判定
- `playlist.py`: プレイリスト作成・追加・ソート
- `youtube_list.py`: YouTube API リスト取得

### ユーティリティスクリプト（utils/）
- `check_playlist_membership.py`: プレイリストメンバーシップ確認・修正
- `check_unuploaded_videos.py`: 未アップロード動画の確認（タイトル一覧ベース）
- `check_should_upload.py`: アップロードすべき動画の確認
- `delete_video.py`: 動画削除（YouTube + uploaded_from_youtube.txt 更新）

