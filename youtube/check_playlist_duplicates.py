#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
指定年のYouTubeプレイリストに同じ動画が複数含まれていないかチェックする。
オプションで重複をプレイリストから削除できる。

使い方:
    チェックのみ（削除しない）:
        python check_playlist_duplicates.py --year 2023
    重複を削除する:
        python check_playlist_duplicates.py --year 2023 --remove
"""

import sys
from pathlib import Path

parent_dir = Path(__file__).resolve().parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from utils import youtube_list
from utils import playlist


def check_playlist_duplicates(year: str, remove: bool = False) -> bool:
    """
    指定年のプレイリストで重複動画をチェックする。remove=True なら重複を削除する。

    Returns:
        重複が1件もない場合 True、重複があった場合 False（削除後も False）
    """
    youtube = youtube_list.get_youtube_service(scope=youtube_list.YOUTUBE_ADMIN_SCOPE)
    playlist_id = playlist.create_or_get_playlist(year, youtube)
    if not playlist_id:
        print(f"Playlist for year '{year}' not found.")
        return True

    items = youtube_list.get_playlist_items(playlist_id, youtube)
    if not items:
        print(f"Playlist {year} has no items.")
        return True

    # videoId ごとに (index, item) のリストを集める
    by_video_id = {}
    for idx, item in enumerate(items):
        video_id = item["snippet"]["resourceId"]["videoId"]
        title = item["snippet"].get("title", "")
        if video_id not in by_video_id:
            by_video_id[video_id] = []
        by_video_id[video_id].append((idx, item["id"], title))

    duplicates = {vid: entries for vid, entries in by_video_id.items() if len(entries) > 1}

    print(f"Playlist: {year} (ID: {playlist_id})")
    print(f"Total items: {len(items)}")
    print(f"Unique videos: {len(by_video_id)}")
    print(f"Duplicates: {'No' if not duplicates else f'Yes ({sum(len(e) - 1 for e in duplicates.values())} extra copy/copies)'}")

    if not duplicates:
        return True

    print("\nDuplicate entries (first occurrence kept, following would be removed):")
    for video_id, entries in sorted(duplicates.items(), key=lambda x: x[1][0][0]):
        print(f"  videoId={video_id} (appears {len(entries)} times)")
        for i, (idx, pl_item_id, title) in enumerate(entries):
            tag = " [KEEP]" if i == 0 else " [REMOVE]"
            print(f"    [{idx}] {title}{tag}")

    if remove:
        print("\nRemoving duplicates...")
        removed = playlist.remove_duplicate_playlist_items(playlist_id, youtube)
        print(f"Removed {removed} duplicate item(s).")
    else:
        print("\nTo remove these duplicates, run with --remove")

    return False


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Check for duplicate videos in a year playlist; optionally remove them"
    )
    parser.add_argument("--year", default="2023", help="Year of the playlist (default: 2023)")
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove duplicate entries from the playlist (keeps first occurrence)",
    )
    args = parser.parse_args()

    try:
        no_duplicates = check_playlist_duplicates(args.year, remove=args.remove)
        sys.exit(0 if no_duplicates else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
