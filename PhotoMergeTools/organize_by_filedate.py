#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
指定フォルダ内のファイルを「ファイルの更新日時」を日付とみなして、
日付フォルダ（YYYY-MM-DD）に整理するスクリプト。

使い方:
  python organize_by_filedate.py ソースフォルダ 移動先の親フォルダ [--dry-run] [--copy]
  例: python organize_by_filedate.py "G:/Users/chiyo/Pictures/iPhone_Child/SDCard/Recovered" "G:/Users/chiyo/Pictures/iPhone_Child"
  --dry-run: 実際には移動せず、実行予定のみ表示
  --copy: 移動ではなくコピー
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime

# 写真・動画として扱う拡張子
MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".heic", ".gif", ".bmp", ".tiff", ".tif",
    ".mov", ".mp4", ".m4v", ".avi", ".m2ts", ".mts",
}


def main():
    args = [a for a in sys.argv[1:] if a in ("--dry-run", "--copy")]
    paths = [a for a in sys.argv[1:] if a not in ("--dry-run", "--copy")]
    dry_run = "--dry-run" in args
    do_copy = "--copy" in args

    if len(paths) < 2:
        print("使い方: python organize_by_filedate.py ソースフォルダ 移動先の親フォルダ [--dry-run] [--copy]")
        print("例: python organize_by_filedate.py \".../iPhone_Child/SDCard/Recovered\" \".../iPhone_Child\"")
        sys.exit(1)

    source_dir = Path(paths[0]).resolve()
    target_parent = Path(paths[1]).resolve()

    if not source_dir.is_dir():
        print(f"エラー: ソースフォルダが見つかりません: {source_dir}")
        sys.exit(1)
    if not target_parent.is_dir():
        print(f"エラー: 移動先の親フォルダが見つかりません: {target_parent}")
        sys.exit(1)

    files = [p for p in source_dir.iterdir() if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS]
    if not files:
        print(f"対象ファイルがありません: {source_dir}")
        sys.exit(0)

    print(f"ソース: {source_dir}")
    print(f"移動先の親: {target_parent}")
    print(f"モード: {'ドライラン（実際には移動しない）' if dry_run else 'コピー' if do_copy else '移動'}")
    print()
    print("実行予定:")
    print("-" * 60)

    for p in sorted(files):
        mtime = p.stat().st_mtime
        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        date_folder = target_parent / date_str
        dest = date_folder / p.name
        if not dry_run:
            date_folder.mkdir(parents=True, exist_ok=True)
            if dest.exists() and dest.resolve() != p.resolve():
                # 同名ファイルが既にある場合は連番を付ける
                stem, ext = p.stem, p.suffix
                n = 1
                while dest.exists():
                    dest = date_folder / f"{stem}_{n}{ext}"
                    n += 1
            if do_copy:
                shutil.copy2(p, dest)
                print(f"  コピー: {p.name} -> {date_str}/")
            else:
                shutil.move(str(p), str(dest))
                print(f"  移動: {p.name} -> {date_str}/")
        else:
            print(f"  {p.name} (更新日: {date_str}) -> {date_str}/")

    print("-" * 60)
    print(f"完了: {len(files)} 件" + ("（ドライラン）" if dry_run else ""))


if __name__ == "__main__":
    main()
