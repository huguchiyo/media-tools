#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本来アップロードすべき動画を確認するスクリプト。

moved_videos_log.json に記録されている動画のうち、
data/uploaded_from_youtube.txt に記載されていない動画を特定します。
"""

import os
import json
import sys
from pathlib import Path

from utils import paths


def load_moved_videos(moved_log_path: str):
    """移動済み動画ログを読み込み"""
    moved_videos = []
    with open(moved_log_path, 'r', encoding='utf-8') as f:
        log_data = json.load(f)
        for entry in log_data:
            for file_info in entry.get('moved_files', []):
                moved_videos.append({
                    'new_name': file_info.get('new_name', ''),
                    'year': file_info.get('year', ''),
                    'full_path': os.path.join(entry.get('target_dir', ''), file_info.get('dest', ''))
                })
    return moved_videos

def load_uploaded_titles(path: Path) -> set:
    """1行1タイトルのファイルを読み込み"""
    titles = set()
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                t = line.strip()
                if t:
                    titles.add(t)
    return titles


def main():
    moved_log_path = paths.PROJECT_ROOT.parent / 'VideoMoveTools' / 'moved_videos_log.json'
    uploaded_path = paths.UPLOADED_FROM_YOUTUBE_PATH

    moved_log_path = os.path.abspath(moved_log_path)
    uploaded_path = os.path.abspath(uploaded_path)

    moved_videos = load_moved_videos(str(moved_log_path))
    uploaded_all = load_uploaded_titles(paths.UPLOADED_FROM_YOUTUBE_PATH)

    print("=" * 80)
    print("本来アップロードすべき動画の確認")
    print("=" * 80)
    print(f"移動済み動画: {len(moved_videos)}件")
    print(f"uploaded_from_youtube.txtに記載: {len(uploaded_all)}件")
    print()
    
    # 本来アップロードすべき動画を特定
    should_upload = []
    for video in moved_videos:
        new_name = video['new_name']
        year = video['year']
        
        # タイトル形式に変換（file_utils と同一ロジック）
        title = (new_name.rsplit('.', 1)[0] if '.' in new_name else new_name).replace('_', ' ')
        full_title = f"{year} {title}"
        
        # アップロード済みかチェック
        if full_title not in uploaded_all:
            should_upload.append({
                'year': year,
                'file': new_name,
                'title': full_title,
                'full_path': video['full_path']
            })
    
    print(f"本来アップロードすべき動画: {len(should_upload)}件")
    print()
    
    # 年ごとにグループ化
    by_year = {}
    for video in should_upload:
        year = video['year']
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(video)
    
    for year in sorted(by_year.keys()):
        videos = by_year[year]
        print(f"{year}年: {len(videos)}件")
        for video in videos:
            print(f"  - {video['file']}")
        print()
    
    print(f"まだアップロードしていない動画: {len(should_upload)}件")
    if should_upload:
        for video in should_upload[:20]:
            print(f"  - {video['file']}")
        if len(should_upload) > 20:
            print(f"  ... and {len(should_upload) - 20} more")

if __name__ == '__main__':
    main()

