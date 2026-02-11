# iPhone写真フォルダ マージツール

このフォルダには、iPhone写真フォルダの重複分析とマージに使用したスクリプトとレポートが含まれています。

## スクリプト一覧

### 重複分析スクリプト
- **analyze_duplicates_generic.py**: 汎用版の重複分析スクリプト（任意のフォルダを指定可能）

### マージスクリプト
- **merge_photos_generic.py**: 汎用版のマージスクリプト（任意のフォルダを指定可能）⭐推奨

## レポートファイル

- **duplicate_report.txt**: Naokiフォルダの重複分析レポート
- **duplicate_report_michino.txt**: Michinoフォルダの重複分析レポート
- **merge_verification_report.txt**: Naokiマージ結果の確認レポート

## 使用方法

### 汎用版マージスクリプトの使い方

```bash
# DRY RUN（実際にはコピーしない）
python merge_photos_generic.py <folder1> <folder2> <output_folder>

# 実際にマージ実行
python merge_photos_generic.py --execute <folder1> <folder2> <output_folder>

# 例
python merge_photos_generic.py --execute iPhone_12_Michino iPhone_Michino iPhone_Michino_Merged
```

### 汎用版重複分析スクリプトの使い方

```bash
python analyze_duplicates_generic.py <folder1> <folder2> [output_report]

# 例
python analyze_duplicates_generic.py iPhone_12_Michino iPhone_Michino duplicate_report.txt
```

## マージの動作

- **HEIC優先**: 同じIMG番号でHEICとJPGがある場合、HEICを優先
- **重複除去**: 完全に同一ファイル（名前・拡張子・サイズ）は1つだけ保持
- **元フォルダ保持**: 元のフォルダは変更されません（新しいフォルダにコピー）

## 実行履歴

- **Naokiマージ**: iPhone_16_Naoki + iPhone_Naoki → iPhone_Merged
- **Michinoマージ**: iPhone_12_Michino + iPhone_Michino → iPhone_Michino_Merged

