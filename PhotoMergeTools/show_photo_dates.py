#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
指定フォルダ内の写真の撮影日（EXIF）を表示するスクリプト。

EXIF の DateTimeOriginal（撮影日時）を読み取ります。
取得できない場合はファイルの更新日時を表示します。

使い方:
  python show_photo_dates.py [フォルダパス]
  例: python show_photo_dates.py "G:/Users/chiyo/Pictures/iPhone_Child/SDCard"
  引数なし: カレントディレクトリ
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 写真として扱う拡張子
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".gif", ".bmp", ".tiff", ".tif"}

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def get_exif_date(path: Path) -> Optional[str]:
    """写真から EXIF の撮影日時を取得。取得できない場合は None。"""
    if not HAS_PIL:
        return None
    try:
        img = Image.open(path)
        exif = img.getexif()
        if exif is None:
            return None
        # DateTimeOriginal = 36867
        for tag_id, value in exif.items():
            if TAGS.get(tag_id) == "DateTimeOriginal":
                return value
        return None
    except Exception:
        return None


def main():
    if len(sys.argv) >= 2:
        folder = Path(sys.argv[1]).resolve()
    else:
        folder = Path.cwd()

    if not folder.is_dir():
        print(f"エラー: フォルダが見つかりません: {folder}")
        sys.exit(1)

    if not HAS_PIL:
        print("Pillow をインストールしてください: pip install Pillow")
        sys.exit(1)

    files = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in PHOTO_EXTENSIONS)
    print(f"フォルダ: {folder}")
    print(f"写真ファイル数: {len(files)}")
    print()
    print("ファイル名\t撮影日（EXIF）\t備考")
    print("-" * 70)

    for p in files:
        rel = p.relative_to(folder) if folder in p.parents or p.parent == folder else p.name
        exif_date = get_exif_date(p)
        if exif_date:
            # EXIF 日時は "2024:06:15 12:30:45" 形式
            try:
                dt = datetime.strptime(exif_date, "%Y:%m:%d %H:%M:%S")
                date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                date_str = exif_date
            note = ""
        else:
            # フォールバック: ファイルの更新日時
            mtime = p.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            note = "(EXIFなし・ファイル日時)"
        print(f"{rel}\t{date_str}\t{note}")
    print("-" * 70)


if __name__ == "__main__":
    main()
