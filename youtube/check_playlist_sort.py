#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
指定年のYouTubeプレイリストが撮影日順にソートされているか確認するスクリプト。

使い方:
    python check_playlist_sort.py --year 2015
"""

import re
import sys
from pathlib import Path

parent_dir = Path(__file__).resolve().parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from utils import youtube_list
from utils import playlist


def extract_date_from_title(title: str) -> tuple:
    """タイトルから (年, 月, 日) を抽出。playlist.sort_playlist_by_date と同じロジック。"""
    match = re.match(r'^(\d{4})\s+(\d{4})', title)
    if match:
        y = int(match.group(1))
        md = match.group(2)
        m = int(md[:2])
        d = int(md[2:])
        return (y, m, d)
    return (0, 0, 0)


def check_playlist_sort_order(year: str):
    youtube = youtube_list.get_youtube_service(scope=youtube_list.YOUTUBE_ADMIN_SCOPE)
    playlist_id = playlist.create_or_get_playlist(year, youtube)
    if not playlist_id:
        print(f"Playlist for year '{year}' not found.")
        return False

    items = youtube_list.get_playlist_items(playlist_id, youtube)
    if not items:
        print(f"Playlist {year} has no items. (Sorted trivially.)")
        return True

    # 現在の並び順で日付を取得
    order = [extract_date_from_title(item['snippet']['title']) for item in items]
    titles = [item['snippet']['title'] for item in items]

    # ソート済みかチェック
    is_sorted = all(order[i] <= order[i + 1] for i in range(len(order) - 1))

    print(f"Playlist: {year} (ID: {playlist_id})")
    print(f"Total items: {len(items)}")
    print(f"Sorted by date (YYYY MMDD): {'Yes' if is_sorted else 'No'}")

    if not is_sorted:
        print("\nOut-of-order pairs (current index -> title):")
        for i in range(len(order) - 1):
            if order[i] > order[i + 1]:
                print(f"  [{i}] {titles[i]}")
                print(f"  [{i+1}] {titles[i+1]}  <- earlier date should come first")

    # 先頭・末尾を数件表示
    print("\nFirst 5 items (current order):")
    for i, (t, d) in enumerate(zip(titles[:5], order[:5])):
        print(f"  {i}: {t}  -> {d[0]}/{d[1]:02d}/{d[2]:02d}")
    if len(titles) > 5:
        print("  ...")
    print("\nLast 3 items (current order):")
    for i, (t, d) in enumerate(zip(titles[-3:], order[-3:]), start=len(titles) - 3):
        print(f"  {i}: {t}  -> {d[0]}/{d[1]:02d}/{d[2]:02d}")

    return is_sorted


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Check if a year playlist is sorted by date')
    parser.add_argument('--year', default='2015', help='Year of the playlist (default: 2015)')
    args = parser.parse_args()

    try:
        ok = check_playlist_sort_order(args.year)
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
