#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YouTube APIから取得した内容を確認するテストスクリプト"""

import youtube_list

# アップロード済み動画のタイトルを取得
print("YouTube APIから動画タイトルを取得中...")
try:
    items = youtube_list.get_upload_titles()
    print(f"\n取得した動画数: {len(items)}")
    print("\n最初の10件:")
    for i, item in enumerate(items[:10], 1):
        title = item["snippet"]["title"]
        print(f"  {i}. {title}")
    
    print("\n最後の10件:")
    for i, item in enumerate(items[-10:], len(items)-9):
        title = item["snippet"]["title"]
        print(f"  {i}. {title}")
        
except Exception as e:
    print(f"エラー: {e}")

