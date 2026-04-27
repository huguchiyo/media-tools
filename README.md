# Tools

写真・動画のインポート後から YouTube アップロードまでを一連の流れで扱うためのツール群です。

**日々の操作はブラウザの「写真・動画ツール」UI から行う想定です。** リポジトリ直下の **`start_server.bat`** をダブルクリックするか、`photo_video_ui` の手順で起動してください。  
`workflow.py` による一括実行は CLI 向けの補助手段で、**通常は使いません**（後述の「ワークフロースクリプト」参照）。

---

## Cursor / AI を使って YouTube Upload まで進める

このリポジトリは、Cursor などで AI に README を読ませながら進めるとセットアップしやすい構成です。  
初見の人は、次の順番で AI に確認させながら進めると、YouTube へのアップロードまで到達しやすくなります。

### 1. リポジトリをクローンしてセットアップする

1. このリポジトリをクローンする。  
2. Cursor でリポジトリを開く。  
3. AI に **`README.md`**, **`photo_video_ui/README.md`**, **`youtube/README.md`** を読ませて、「YouTube アップロードまでに必要な作業を順番に教えて」と依頼する。  
4. 必要な Python 依存を入れる。**UI の起動だけでなく、YouTube 認証ボタン / アップロード実行にも追加ライブラリが必要**です。初回セットアップ時に最低限、次を入れておく。  

```bash
pip install -r photo_video_ui/requirements.txt
pip install google-api-python-client google-auth-oauthlib httplib2
```

依存が不足していると、UI 上で **「YouTube 認証を行う」** を押したときに `ModuleNotFoundError: No module named 'httplib2'` のようなエラーで止まります。  
特に YouTube 関連は `google-api-python-client`, `google-auth-oauthlib`, `httplib2` が必要です。

### 2. Google Cloud 側を準備する

YouTube へアップロードするには、Google Cloud 側の設定が必要です。AI に画面遷移を案内させながら進めるのがおすすめです。

必要な作業:

1. Google Cloud でプロジェクトを作成または選択する。  
2. **YouTube Data API v3** を有効化する。  
3. **OAuth 同意画面**を設定する。  
4. 認証情報で **OAuth クライアント ID** を作成する。  
   - 推奨: **デスクトップ アプリ**  
5. テスト中のアプリとして使う場合は、**自分の Google アカウントをテストユーザーに追加**する。  
6. ダウンロードした JSON を `youtube/client_secrets.json` として配置する。  

AI には、たとえば次のように頼むと進めやすいです。

- 「このリポジトリの `youtube/client_secrets.json` に必要な Google Cloud Console の設定を案内して」
- 「OAuth 同意画面とテストユーザー設定で詰まりやすい点を教えて」

### 3. ローカル設定ファイルを作る

1. `youtube/config.json.example` をコピーして `youtube/config.json` を作る。  
2. 必要なら `target_dir` などの設定をローカル環境に合わせて修正する。  

このファイルや認証ファイルは個人環境依存なので、コミットしません。

### 4. UI を起動する

ブラウザ UI を使う場合は、次のいずれかで起動します。

- **`Tools/start_server.bat`** をダブルクリック（推奨）  
- または `photo_video_ui/start_server.bat` をダブルクリック  
- または `photo_video_ui/app.py` を Python で起動  

起動後、ブラウザで `http://127.0.0.1:5151` を開きます。

### 5. YouTube 認証を完了する

UI からアップロードする前に、**「YouTube 認証を行う」** を使って OAuth 認証を完了させます。

1. UI を開く。  
2. **「YouTube 認証を行う」** を押す。  
3. ブラウザで Google ログインと権限許可を行う。  
4. 認証後、`youtube/youtube-admin-oauth2.json` が作成される。  

認証ボタンで `ModuleNotFoundError` が出る場合は、先に上記の Python 依存をインストールしてください。

もし `403 access_denied` や `insufficient authentication scopes` が出た場合は、次を確認します。

- Google Cloud 側でテストユーザーに自分を追加しているか  
- OAuth 同意画面が正しく設定されているか  
- 必要なら `youtube/clear_oauth_token.py` でトークンを削除して再認証する  

### 6. 分離とアップロードを実行する

1. UI で **指定フォルダ**（例: カメラのインポート先）と **動画保存用フォルダ**（例: 年別に整理した動画の置き場）を設定する。  
2. まず **プレビュー（ドライラン）** で分離結果を確認する。  
3. 必要なら **分離を実行**し、動画を年フォルダへ移動する。  
4. **動画保存用フォルダ**直下のフォルダを選び、YouTube にアップロードする。  

### 7. AI に依頼するときのおすすめ

Cursor の AI には、次のように頼むと進めやすいです。

- 「このリポジトリで YouTube アップロードまでに必要な手順を README ベースで整理して」
- 「Google Cloud Console の設定で足りない点を確認して」
- 「`client_secrets.json` を配置したので、認証テストして」
- 「UI を起動して dry-run で問題ないか確認して」

### 8. よく詰まるポイント

- `client_secrets.json` のファイル名が違う  
- YouTube Data API v3 を有効化していない  
- OAuth 同意画面の設定不足  
- テストユーザー未追加で `403 access_denied`  
- Python 依存が不足していて UI や YouTube スクリプトが起動しない  
- `httplib2` などの YouTube 用依存が不足していて、**「YouTube 認証を行う」** で `ModuleNotFoundError` が出る  

迷ったら、まず AI に **`README.md` / `photo_video_ui/README.md` / `youtube/README.md` を読ませたうえで、今どこで詰まっているか** を伝えるのがおすすめです。

---

## UI で使う（写真・動画ツール）

分離（カメラ等 → 動画保存用フォルダ）と YouTube アップロードをブラウザから行います。操作手順・トラブルシュートは **[photo_video_ui/README.md](photo_video_ui/README.md)** を参照してください。

- 起動: **`start_server.bat`**（リポジトリ直下）または `photo_video_ui/start_server.bat`  
- URL: `http://127.0.0.1:5151`

---

## ワークフロー概要（4ステップ）

UI でも CLI でも、おおまかなデータの流れは次のとおりです。

| # | 内容 | 担当 | 記録先 |
|---|------|------|--------|
| 1 | **camera**（等）の動画をリネームして **movie**（動画保存用フォルダ）に移動 | VideoMoveTools | — |
| 2 | どのフォルダにどの動画が移動したかを記録し、結果を表示 | VideoMoveTools | `VideoMoveTools/moved_videos_log.json`（確認用: `moved_videos_log.md`） |
| 3 | movie の動画のうち未アップロードを確認し結果を表示。該当年を YouTube にアップロード | youtube | — |
| 4 | アップロード結果を記録 | youtube | `youtube/data/upload_runs.json`（確認用: `upload_runs.md`）および `uploaded_from_youtube.txt` |

- **1・2**: [VideoMoveTools](VideoMoveTools/README.md) のリネーム規則に従い、`camera`（または指定ソース）の動画を `movie/YYYY/` に移動し、その結果を `moved_videos_log.json` に追記します。ソース直下の動画も対象で、ファイル名・メタデータ・更新日時から日付を推定します。実行後は**移動結果（年ごとの一覧）を表示**します。
- **3**: **movie フォルダ**をスキャンし、`youtube/data/uploaded_from_youtube.txt` に載っていない動画を**未アップロードとして一覧表示**します。該当する年のフォルダを YouTube にアップロードするか確認してから本番実行します。
- **4**: 各アップロード実行ごとに `youtube_upload.py` が成功・スキップ・失敗件数を `youtube/data/upload_runs.json` に追記し、アップロード済みタイトルは `uploaded_from_youtube.txt` に追記します。

## 個別ツール

- **[VideoMoveTools](VideoMoveTools/README.md)**  
  - 動画のリネーム規則・移動先・重複判定・`moved_videos_log.json` の形式はここに記載されています。
- **[youtube](youtube/README.md)**  
  - アップロードの詳細オプション、認証、`uploaded_from_youtube.txt` / `upload_runs.json` の扱いはここを参照してください。
- **PhotoMergeTools**  
  - 写真のマージ・重複分析用。動画ワークフローとは独立しています。

## ワークフロースクリプト（`workflow.py`）（参考）

**通常は UI から操作するため、このスクリプトは使わなくて問題ありません。** ターミナルだけで移動とアップロードを連続実行したい場合の CLI 用です。

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

## フォルダ構成の想定

- **camera**: インポートした写真・動画が入るフォルダ（日付フォルダや年フォルダ、または写真・動画が直下に混在するフォルダ）。
- **movie**: 動画のみリネーム後に年ごとに格納するフォルダ（`movie/2024/`, `movie/2025/` など）。
- **movie/unknown**: 日付を推定できなかった動画の退避先。

移動先ベースは VideoMoveTools のデフォルト（`movie`）または `--target` で指定。アップロード時は `--movie-dir`（既定で同じ movie パス）でスキャンし、未アップロード判定に `uploaded_from_youtube.txt` を使います。

---

## GitHub にアップするとき／クローン後のセットアップ

- **コミットしないもの**（`.gitignore` で除外済み）  
  - 認証: `youtube/client_secrets.json`, `youtube/config.json`, `youtube/*-oauth2.json`  
  - ログ: `youtube/logs/*.log`  
  - 実行結果・個人データ: `youtube/data/uploaded_*.txt`, `upload_runs.*`, `VideoMoveTools/moved_videos_log.*`, `photo_video_ui/data/`  
  - バックアップ: `*.backup`, `*.bak`

- **クローン後にやること**  
  1. `youtube/config.json.example` をコピーして `youtube/config.json` を作成し、必要ならパス等を編集。  
  2. [Google API Console](https://console.cloud.google.com/) で OAuth 2.0 クライアントを作成し、`youtube/client_secrets.json` を配置。  
  3. `pip install -r photo_video_ui/requirements.txt`（UI を使う場合）。  
  4. 初回のアップロードまたは UI の「YouTube 認証を行う」でブラウザからログインし、トークンを発行する。
