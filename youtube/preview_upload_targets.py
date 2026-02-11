#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アップロード対象動画の事前確認スクリプト。

YouTube API でアップロード済み一覧を取得し、指定フォルダ内の動画のうち
「まだ YouTube にない」ものだけを一覧表示します。アップロードは行いません。

使い方:
    python preview_upload_targets.py --dir "G:/Users/chiyo/Pictures/movie/2025"
    python preview_upload_targets.py --dir "G:/Users/chiyo/Pictures/movie/2025" --output data/upload_targets.txt
"""

import os
import sys
from pathlib import Path

parent_dir = Path(__file__).resolve().parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from utils import youtube_list
from utils import file_utils


def main():
    # oauth2client 用に --dir / --output を先に取り除く
    dir_path = None
    output_path = None
    argv = sys.argv[1:]
    new_argv = []
    i = 0
    while i < len(argv):
        if argv[i] in ('--dir', '-d'):
            if i + 1 < len(argv):
                dir_path = argv[i + 1]
                i += 2
            else:
                i += 1
            continue
        if argv[i] in ('--output', '-o'):
            if i + 1 < len(argv):
                output_path = argv[i + 1]
                i += 2
            else:
                i += 1
            continue
        new_argv.append(argv[i])
        i += 1
    sys.argv = [sys.argv[0]] + new_argv

    if not dir_path:
        print('Usage: python preview_upload_targets.py --dir <target_directory> [--output <file>]', file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(dir_path):
        print(f'Error: directory not found: {dir_path}', file=sys.stderr)
        sys.exit(1)

    # 1. YouTube API でアップロード済み一覧を取得
    print('Fetching uploaded video list from YouTube API...', file=sys.stderr)
    try:
        videos = youtube_list.get_upload_titles(youtube=None, scope=youtube_list.YOUTUBE_READONLY_SCOPE)
        uploaded_titles = {v['snippet']['title'] for v in videos}
        print(f'Got {len(uploaded_titles)} uploaded video(s) from YouTube.', file=sys.stderr)
    except Exception as e:
        print(f'Error fetching from YouTube API: {e}', file=sys.stderr)
        sys.exit(1)

    # 2. 指定フォルダ内の動画のうち、API 一覧にないものをアップロード対象とする
    files = [
        f for f in os.listdir(dir_path)
        if os.path.isfile(os.path.join(dir_path, f)) and file_utils.is_video_file(f)
    ]
    files.sort()

    targets = []
    for f in files:
        title = file_utils.modify_movie_name(f)
        if title is None:
            continue
        if title not in uploaded_titles:
            targets.append((title, f))

    # 3. 結果を表示またはファイルに保存
    print(f'\nDirectory: {dir_path}', file=sys.stderr)
    print(f'Local video files: {len(files)}', file=sys.stderr)
    print(f'Already on YouTube (skipped): {len(files) - len(targets)}', file=sys.stderr)
    print(f'Upload targets (not on YouTube): {len(targets)}\n', file=sys.stderr)

    lines = []
    for title, filename in targets:
        line = f"{title}\t{filename}"
        lines.append(line)
        if not output_path:
            print(line)

    if output_path:
        out = Path(output_path)
        if not out.is_absolute():
            out = parent_dir / out
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, 'w', encoding='utf-8') as fp:
            fp.write('\n'.join(lines) + '\n')
        print(f'Saved {len(lines)} upload targets to {out}', file=sys.stderr)


if __name__ == '__main__':
    main()
