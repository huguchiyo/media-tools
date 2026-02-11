#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube API でアップロード済み動画の名前（タイトル）一覧を取得するスクリプト。

使い方:
    python list_uploaded_videos.py
    python list_uploaded_videos.py --output uploaded_from_youtube.txt
"""

import os
import sys
from pathlib import Path

# スクリプトの親ディレクトリをパスに追加
parent_dir = Path(__file__).resolve().parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from utils import youtube_list


def main():
    # oauth2client が sys.argv を解析するため、先に --output を抜き出して取り除く
    output_path = None
    argv = sys.argv[1:]
    new_argv = []
    i = 0
    while i < len(argv):
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

    # 読み取り専用スコープで認証してアップロード一覧を取得
    print('Connecting to YouTube API (read-only)...', file=sys.stderr)
    videos = youtube_list.get_upload_titles(youtube=None, scope=youtube_list.YOUTUBE_READONLY_SCOPE)

    if not videos:
        print('No uploaded videos found (or API error).', file=sys.stderr)
        sys.exit(1)

    titles = [v['snippet']['title'] for v in videos]
    titles.sort()

    print(f'Found {len(titles)} uploaded video(s).', file=sys.stderr)

    if output_path:
        out_path = Path(output_path)
        if not out_path.is_absolute():
            out_path = parent_dir / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            for t in titles:
                f.write(t + '\n')
        print(f'Saved to {out_path}', file=sys.stderr)
    else:
        for t in titles:
            print(t)


if __name__ == '__main__':
    main()
