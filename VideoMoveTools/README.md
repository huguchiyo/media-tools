# 動画ファイル移動ツール

このフォルダには、動画ファイルを日付フォルダから`movie`フォルダに移動・リネームするスクリプトが含まれています。

## スクリプト一覧

### 動画移動スクリプト
- **move_videos_to_movie.py**: 動画ファイルをソースフォルダから`movie`フォルダに移動し、リネームするスクリプト

## 使用方法

### 基本的な使い方

```bash
# DRY RUN（実際には移動しない）
python move_videos_to_movie.py --dry-run

# 実際に移動実行（確認プロンプトあり）
python move_videos_to_movie.py --execute

# 実際に移動実行（確認プロンプトなし）
python move_videos_to_movie.py --execute-yes
```

### オプション

- `--source SOURCE_DIR`: ソースフォルダを指定（複数指定可能）
- `--target TARGET_DIR`: 移動先フォルダを指定（デフォルト: `movie`）
- `--dry-run`: ドライランモード（実際には移動しない）
- `--execute`: 実行モード（確認プロンプトあり）
- `--execute-yes`: 実行モード（確認プロンプトなし）

### 例

```bash
# 特定のフォルダのみ処理
python move_videos_to_movie.py --source camera --dry-run

# 複数のフォルダを指定
python move_videos_to_movie.py --source camera --source <other_folder> --dry-run
```

## 動作

### 処理対象フォルダ（デフォルト）
- `camera`

### リネーム規則
- 日付フォルダ内の動画: `IMG_0363.MOV` → `2025_0102_IMG_0363.MOV`（年_月日_元のファイル名）
- 年フォルダ内の動画: 既にリネーム済みの場合はそのまま移動

### 重複判定
- 移動先の年フォルダに**同じファイル名**が既にある場合、重複とみなしてスキップし、ソースのファイルを削除します（ファイル名のみで判定、ハッシュは使いません）。

### 移動先
- `movie/YYYY/` フォルダ（年ごとに整理）

### ログ
- 移動記録は `Tools/VideoMoveTools/moved_videos_log.json` に保存されます
- 人が確認しやすい一覧は `moved_videos_log.md` に同じ内容で出力されます（実行のたびに全体を再生成）

## 実行履歴

- **2026-01-04**: 初回実行
  - 処理対象: 264個
  - 移動: 52個
  - スキップ（重複）: 212個

