# YouTube動画アップロードツール

YouTubeに動画をアップロードするPythonスクリプトです。

## ディレクトリ構造

```
Tools/youtube/
├── youtube_upload.py          # メインスクリプト（動画アップロード）
├── clear_oauth_token.py       # OAuthトークン削除（403時など）
├── config.json                 # 設定ファイル
├── client_secrets.json         # OAuth認証情報
├── README.md                   # メインドキュメント
│
├── utils/                      # ライブラリ・ユーティリティ
│   ├── paths.py                # 共通パス（data/, uploaded_from_youtube.txt）
│   ├── auth.py                 # 認証（OAuth 2.0）
│   ├── upload.py               # アップロード処理
│   ├── file_utils.py           # ファイル名・動画判定
│   ├── playlist.py             # プレイリスト操作
│   ├── youtube_list.py         # YouTube API リスト操作
│   ├── check_playlist_membership.py
│   ├── check_unuploaded_videos.py
│   ├── check_should_upload.py
│   ├── parse_upload_log.py       # ログから直近実行の詳細を取得（UI表示用）
│   └── delete_video.py
│
├── tests/                      # テストスクリプト
│   └── test_api.py
│
├── data/                       # データファイル
│   ├── uploaded_from_youtube.txt  # アップロード済み一覧（スキップ判定・成功時に追記）
│   ├── upload_runs.json        # アップロード実行結果の履歴（JSON）
│   ├── upload_runs.md          # 上記の人が確認しやすい一覧（実行のたびに再生成）
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

## 機能

- 指定ディレクトリ内の動画ファイルを自動アップロード
- **スキップ判定**: タイトルのみ（`data/uploaded_from_youtube.txt` を参照・追記）。
- `--no-fetch-list`: 起動時に API で一覧取得をスキップし、ローカル一覧のみで判定（短時間で開始）
- 自動プレイリスト作成・追加（年ベース）、プレイリスト内を撮影日順にソート、重複動画の削除
- リジューム可能なアップロード、エラー時リトライ、進捗表示とログ出力

## セットアップ

1. **必要なライブラリのインストール**
```bash
pip install google-api-python-client google-auth-oauthlib httplib2
```

- `httplib2` は OAuth 認証時にも必要です
- `google-auth-oauthlib` はブラウザでの OAuth ログイン処理に使用します
- ブラウザ UI の **「YouTube 認証を行う」** ボタンもこの依存を利用します
- 不足していると `ModuleNotFoundError: No module named 'httplib2'` で認証が始まりません

2. **OAuth認証情報の設定**
   - Google API ConsoleでOAuth 2.0クライアントIDを作成
   - `client_secrets.json`に認証情報を保存

3. **設定ファイルの作成**
```bash
cp config.json.example config.json
# config.jsonを編集して設定を変更
```

## 使用方法

### 基本的な使用方法

```bash
# 年フォルダを指定してアップロード（既定でタイトル一致でスキップ判定）
python youtube_upload.py --dir "G:/path/to/movie/2025"

# API 一覧取得をスキップして短時間で開始（ローカル data/uploaded_from_youtube.txt のみ参照）
python youtube_upload.py --dir "G:/path/to/movie/2025" --no-fetch-list

# Dry-run（実際にはアップロードしない）
python youtube_upload.py --dir "G:/path/to/movie/2025" --dry-run
```

### ユーティリティスクリプトの使用

```bash
# 未アップロード動画の確認
python utils/check_unuploaded_videos.py

# プレイリストメンバーシップの確認・修正
python utils/check_playlist_membership.py --fix

# アップロードすべき動画の確認
python utils/check_should_upload.py

# 直近のアップロード実行の詳細をログから取得（JSON出力・UIでの詳細表示用）
python utils/parse_upload_log.py
```

### 403 Insufficient Permission が出たとき（認証スコープ不足）

アップロード時に「Request had insufficient authentication scopes」と出た場合は、保存されている OAuth トークンにアップロード権限が含まれていません。次のスクリプトでトークンを削除し、再度アップロードを実行するとブラウザで再ログインし、必要な権限を許可できます。

```bash
python clear_oauth_token.py
# 続けてアップロードを実行
python youtube_upload.py --dir "G:/path/to/videos/" --title-only
```

### 設定ファイル (config.json)

```json
{
    "target_dir": "G:/Users/chiyo/Pictures/movie/2025/",
    "movie_tag": "2025年",
    "privacy_status": "private",
    "category_id": "22",
    "uploaded_list_file": "./data/uploaded_list.txt"
}
```

- `target_dir`: アップロードする動画ファイルがあるディレクトリ
- `movie_tag`: 動画の説明文（タグ）
- `privacy_status`: プライバシー設定（`public`, `private`, `unlisted`）
- `category_id`: カテゴリID（22 = People & Blogs）
- `uploaded_list_file`: アップロード済みリストファイルのパス（推奨: `./data/uploaded_list.txt`）

## 仕様

### ファイル名の処理

- 拡張子を除去
- アンダースコア（`_`）をスペースに置換
- 例: `2018_0426_111029.m2ts` → `2018 0426 111029`

### アップロード済みリスト

- **テキスト形式** (`data/uploaded_list.txt`): アップロード済みのタイトルを保存（後方互換性のため）
- **JSON形式** (`data/uploaded_list.json`): ハッシュ値、タイトル、動画ID、ファイルパスなどを保存
- 再実行時に既にアップロード済みの動画は自動的にスキップ
- **ハッシュ値ベースの重複判定**: ファイル名が変わっても、同じファイル（ハッシュ値が同じ）なら再アップロードされません
- アップロード前後にYouTube APIから最新のアップロード済みリストを取得して更新

### 対応動画形式

- `.mp4`, `.mov`, `.m2ts`, `.mts`, `.avi`, `.mkv`, `.wmv`, `.flv`, `.webm`

### ログ

- ログは`logs/`ディレクトリに保存されます
- コンソールにも出力されます

## 改善点

### v3.0（最新）
- ✅ **ハッシュ値ベースの重複判定**（ファイル名が変わっても同一ファイルを検出）
- ✅ JSON形式のアップロード済みリスト（`uploaded_list.json`）
- ✅ 自動プレイリスト作成・追加（年ベース）
- ✅ プレイリスト内の動画を撮影日順に自動ソート
- ✅ アップロード前後のYouTube APIからのリスト更新

### v2.0
- ✅ アップロード済みリストへの自動書き込み
- ✅ ファイル名処理のエラー修正
- ✅ パスの結合方法の改善（`os.path.join`使用）
- ✅ コードの重複削減
- ✅ エラーハンドリングの改善
- ✅ ディレクトリ内のファイルフィルタリング（動画ファイルのみ）
- ✅ ログ機能の追加
- ✅ 設定の外部化
- ✅ 型ヒントの追加
- ✅ ドキュメントの追加
- ✅ 進捗表示の改善
- ✅ 不要なコードの削除

## 注意事項

- YouTube APIのクォータ制限に注意してください
- 大量の動画をアップロードする場合は、時間をかけて実行してください
- クォータの確認: [Google YouTube APIの使用状況](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas?folder=&hl=ja&organizationId=&project=youtube-311223)

## トラブルシューティング

### 認証エラー
- `client_secrets.json`が正しく設定されているか確認
- OAuth認証を再度実行してください

### アップロードエラー
- ログファイル（`logs/youtube_upload.log`）を確認
- ファイルサイズや形式を確認
- ネットワーク接続を確認
