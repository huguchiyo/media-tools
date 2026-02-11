#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTubeアップロード済み動画の再生リスト所属確認スクリプト

既にYouTubeにアップロード済みの動画が、適切な再生リスト（年ベース）に
正しく追加されているか確認します。

使用方法:
    python check_playlist_membership.py [--fix]
"""

import sys
import re
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import youtube_list
import youtube_upload

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('check_playlist_membership.log', encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)


def extract_year_from_title(title: str) -> Optional[str]:
    """
    タイトルから年を抽出します（例：2026 0104 TEST VIDEO -> 2026）
    
    Args:
        title: 動画のタイトル
        
    Returns:
        年（文字列）、失敗時はNone
    """
    match = re.match(r'^(\d{4})\s+', title)
    if match:
        return match.group(1)
    return None


def check_playlist_membership(fix: bool = False) -> Dict[str, Any]:
    """
    アップロード済み動画が適切な再生リストに含まれているか確認します。
    
    Args:
        fix: Trueの場合、見つからない動画を自動的に追加します
        
    Returns:
        確認結果の統計情報
    """
    logger.info("=" * 80)
    logger.info("YouTube Playlist Membership Check")
    logger.info("=" * 80)
    
    # YouTube APIサービスを取得
    try:
        youtube = youtube_list.get_youtube_service(scope=youtube_list.YOUTUBE_ADMIN_SCOPE)
    except Exception as e:
        logger.error(f"Failed to authenticate: {e}")
        return {'total': 0, 'in_playlist': 0, 'missing': 0, 'errors': 0}
    
    # アップロード済み動画を取得
    logger.info("Fetching uploaded videos from YouTube...")
    try:
        uploaded_videos = youtube_list.get_upload_titles(youtube=youtube)
        logger.info(f"Found {len(uploaded_videos)} uploaded videos")
    except Exception as e:
        logger.error(f"Failed to fetch uploaded videos: {e}")
        return {'total': 0, 'in_playlist': 0, 'missing': 0, 'errors': 0}
    
    # プレイリスト一覧を取得
    logger.info("Fetching playlists...")
    try:
        playlists = youtube_list.get_playlists(youtube=youtube)
        logger.info(f"Found {len(playlists)} playlists")
    except Exception as e:
        logger.error(f"Failed to fetch playlists: {e}")
        return {'total': 0, 'in_playlist': 0, 'missing': 0, 'errors': 0}
    
    # プレイリストIDのキャッシュ（年 -> プレイリストID）
    playlist_cache: Dict[str, str] = {}
    
    # プレイリスト内の動画IDのキャッシュ（プレイリストID -> set of video IDs）
    playlist_videos_cache: Dict[str, set] = {}
    
    stats = {
        'total': len(uploaded_videos),
        'in_playlist': 0,
        'missing': 0,
        'errors': 0,
        'missing_videos': [],
        'added_videos': []  # 追加した動画の記録
    }
    
    logger.info("=" * 80)
    logger.info("Checking playlist membership...")
    logger.info("=" * 80)
    
    for video in uploaded_videos:
        title = video['snippet']['title']
        video_id = video['snippet']['resourceId']['videoId']
        
        # タイトルから年を抽出
        year = extract_year_from_title(title)
        
        if not year:
            logger.warning(f"Could not extract year from title: {title} (ID: {video_id})")
            stats['errors'] += 1
            continue
        
        # プレイリストIDを取得または作成
        if year not in playlist_cache:
            playlist_id = youtube_list.get_playlist_id(year, playlists)
            if playlist_id:
                playlist_cache[year] = playlist_id
                logger.debug(f"Found playlist for year {year}: {playlist_id}")
            else:
                logger.warning(f"Playlist not found for year {year}: {title} (ID: {video_id})")
                stats['errors'] += 1
                continue
        
        playlist_id = playlist_cache[year]
        
        # プレイリスト内の動画IDを取得（キャッシュから）
        if playlist_id not in playlist_videos_cache:
            try:
                playlist_items = youtube_list.get_playlist_items(playlist_id, youtube=youtube)
                video_ids = {item['snippet']['resourceId']['videoId'] for item in playlist_items}
                playlist_videos_cache[playlist_id] = video_ids
                logger.debug(f"Cached {len(video_ids)} videos for playlist {year}")
            except Exception as e:
                logger.error(f"Failed to get playlist items for {year}: {e}")
                stats['errors'] += 1
                continue
        
        # 動画がプレイリストに含まれているかチェック
        if video_id in playlist_videos_cache[playlist_id]:
            logger.info(f"✓ {title} (ID: {video_id}) -> Playlist: {year}")
            stats['in_playlist'] += 1
        else:
            logger.warning(f"✗ {title} (ID: {video_id}) -> NOT in playlist: {year}")
            stats['missing'] += 1
            stats['missing_videos'].append({
                'title': title,
                'video_id': video_id,
                'year': year,
                'playlist_id': playlist_id
            })
            
            # 自動修正モード
            if fix:
                logger.info(f"  Attempting to add video to playlist {year}...")
                try:
                    if youtube_upload.add_video_to_playlist(video_id, playlist_id, youtube):
                        logger.info(f"  ✓ Successfully added to playlist {year}")
                        # キャッシュを更新
                        playlist_videos_cache[playlist_id].add(video_id)
                        stats['missing'] -= 1
                        stats['in_playlist'] += 1
                        # 追加した動画を記録
                        stats['added_videos'].append({
                            'title': title,
                            'video_id': video_id,
                            'year': year,
                            'playlist_id': playlist_id,
                            'added_at': datetime.now().isoformat()
                        })
                    else:
                        logger.error(f"  ✗ Failed to add to playlist {year}")
                except Exception as e:
                    logger.error(f"  ✗ Error adding to playlist: {e}")
    
    # 結果を表示
    logger.info("=" * 80)
    logger.info("Check Results")
    logger.info("=" * 80)
    logger.info(f"Total videos: {stats['total']}")
    logger.info(f"In playlist: {stats['in_playlist']}")
    logger.info(f"Missing from playlist: {stats['missing']}")
    logger.info(f"Errors: {stats['errors']}")
    
    if stats['missing_videos']:
        logger.info("")
        logger.info("Missing videos:")
        for video in stats['missing_videos']:
            logger.info(f"  - {video['title']} (ID: {video['video_id']}) -> Should be in playlist: {video['year']}")
    
    # 追加した動画の記録を保存
    if fix and stats['added_videos']:
        script_dir = Path(__file__).parent
        record_file = script_dir / 'playlist_additions_log.json'
        
        # 既存の記録を読み込み
        existing_records = []
        if record_file.exists():
            try:
                with open(record_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        existing_records = existing_data
                    elif isinstance(existing_data, dict) and 'additions' in existing_data:
                        existing_records = existing_data['additions']
            except Exception as e:
                logger.warning(f"Failed to load existing records: {e}")
        
        # 新しい記録を追加
        existing_records.extend(stats['added_videos'])
        
        # 記録を保存
        try:
            record_data = {
                'last_updated': datetime.now().isoformat(),
                'total_additions': len(existing_records),
                'additions': existing_records
            }
            with open(record_file, 'w', encoding='utf-8') as f:
                json.dump(record_data, f, ensure_ascii=False, indent=2)
            logger.info("")
            logger.info(f"Saved {len(stats['added_videos'])} addition(s) to: {record_file}")
        except Exception as e:
            logger.error(f"Failed to save addition records: {e}")
    
    return stats


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Check if uploaded videos are in correct playlists')
    parser.add_argument('--fix', action='store_true', help='Automatically add missing videos to playlists')
    
    args = parser.parse_args()
    
    try:
        stats = check_playlist_membership(fix=args.fix)
        
        if stats['missing'] > 0 and not args.fix:
            logger.info("")
            logger.info("To automatically add missing videos to playlists, run with --fix option")
            sys.exit(1)
        elif stats['missing'] == 0:
            logger.info("")
            logger.info("All videos are in their correct playlists! ✓")
            sys.exit(0)
        else:
            sys.exit(0)
    except KeyboardInterrupt:
        logger.info("Check interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

