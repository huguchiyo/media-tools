#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
移動済み動画ファイルの中で、YouTubeにまだアップロードしていない動画を確認するスクリプト。

アップロード済み判定: data/uploaded_from_youtube.txt（タイトル一覧）のみ参照。
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Set, Any, Optional

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('check_unuploaded_videos.log', encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)


def load_moved_videos_log(moved_log_path: str) -> List[Dict[str, Any]]:
    """
    移動済み動画ログを読み込みます。
    
    Args:
        moved_log_path: moved_videos_log.jsonのパス
        
    Returns:
        移動済み動画のリスト
    """
    moved_videos = []
    
    if not os.path.exists(moved_log_path):
        logger.error(f"Moved videos log not found: {moved_log_path}")
        return moved_videos
    
    try:
        with open(moved_log_path, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
            
        # ログファイルは配列形式
        for entry in log_data:
            target_dir = entry.get('target_dir', '')
            moved_files = entry.get('moved_files', [])
            
            for file_info in moved_files:
                dest = file_info.get('dest', '')
                # フルパスを構築
                full_path = os.path.join(target_dir, dest)
                # パスの正規化（バックスラッシュをスラッシュに統一）
                full_path = os.path.normpath(full_path)
                
                moved_videos.append({
                    'full_path': full_path,
                    'dest': dest,
                    'new_name': file_info.get('new_name', ''),
                    'year': file_info.get('year', ''),
                    'original_name': file_info.get('original_name', '')
                })
        
        logger.info(f"Loaded {len(moved_videos)} moved videos from {moved_log_path}")
    except Exception as e:
        logger.error(f"Failed to load moved videos log: {e}")
    
    return moved_videos


def load_uploaded_titles(uploaded_titles_path: str) -> Set[str]:
    """
    アップロード済みタイトル一覧を読み込みます（1行1タイトル、uploaded_from_youtube.txt 用）。
    """
    titles = set()
    if not os.path.exists(uploaded_titles_path):
        return titles
    try:
        with open(uploaded_titles_path, 'r', encoding='utf-8') as f:
            for line in f:
                t = line.strip()
                if t:
                    titles.add(t)
        logger.info(f"Loaded {len(titles)} titles from {uploaded_titles_path}")
    except Exception as e:
        logger.warning(f"Failed to load uploaded titles: {e}")
    return titles


def _title_from_moved_video(video: Dict[str, Any]) -> str:
    """移動ログの new_name からアップロード済みリストと同じタイトル形式を生成"""
    new_name = video.get('new_name', '')
    base = new_name.rsplit('.', 1)[0] if '.' in new_name else new_name
    return base.replace('_', ' ')


def check_unuploaded_videos(
    moved_log_path: str,
    uploaded_titles_path: str,
) -> Dict[str, Any]:
    """
    移動済み動画の中で、まだアップロードされていない動画を確認します。
    アップロード済み判定は data/uploaded_from_youtube.txt（タイトル一覧）のみ。
    """
    logger.info("=" * 80)
    logger.info("Checking unuploaded videos")
    logger.info("=" * 80)
    
    moved_videos = load_moved_videos_log(moved_log_path)
    uploaded_titles = load_uploaded_titles(uploaded_titles_path)
    logger.info(f"Found {len(uploaded_titles)} uploaded videos (by title)")
    
    unuploaded_videos = []
    not_found_files = []
    
    logger.info("")
    logger.info("Checking moved videos...")
    
    for video in moved_videos:
        full_path = video['full_path']
        
        if not os.path.exists(full_path):
            not_found_files.append(video)
            logger.warning(f"File not found: {full_path}")
            continue
        
        full_title = _title_from_moved_video(video)
        if full_title in uploaded_titles:
            logger.debug(f"✓ Uploaded: {video['new_name']}")
        else:
            unuploaded_videos.append(video)
            logger.info(f"✗ Not uploaded: {video['new_name']} ({full_path})")
    
    result = {
        'total_moved': len(moved_videos),
        'total_uploaded': len(uploaded_titles),
        'unuploaded_count': len(unuploaded_videos),
        'not_found_count': len(not_found_files),
        'unuploaded_videos': unuploaded_videos,
        'not_found_files': not_found_files,
    }
    
    # 結果を表示
    logger.info("")
    logger.info("=" * 80)
    logger.info("Check Results")
    logger.info("=" * 80)
    logger.info(f"Total moved videos: {result['total_moved']}")
    logger.info(f"Total uploaded videos: {result['total_uploaded']}")
    logger.info(f"Unuploaded videos: {result['unuploaded_count']}")
    logger.info(f"Files not found: {result['not_found_count']}")
    
    if unuploaded_videos:
        logger.info("")
        logger.info("Unuploaded videos:")
        # 年ごとにグループ化
        by_year: Dict[str, List[Dict]] = {}
        for video in unuploaded_videos:
            year = video.get('year', 'Unknown')
            if year not in by_year:
                by_year[year] = []
            by_year[year].append(video)
        
        for year in sorted(by_year.keys()):
            videos = by_year[year]
            logger.info(f"  {year}: {len(videos)} videos")
            for video in videos[:5]:  # 最初の5件だけ表示
                logger.info(f"    - {video['new_name']}")
            if len(videos) > 5:
                logger.info(f"    ... and {len(videos) - 5} more")
    
    if not_found_files:
        logger.info("")
        logger.info("Files not found:")
        for video in not_found_files[:10]:  # 最初の10件だけ表示
            logger.info(f"  - {video['full_path']}")
        if len(not_found_files) > 10:
            logger.info(f"  ... and {len(not_found_files) - 10} more")
    
    return result


def save_result_json(result: Dict[str, Any], output_path: str) -> None:
    """
    結果をJSONファイルに保存します。
    
    Args:
        result: 結果の辞書
        output_path: 出力ファイルパス
    """
    try:
        from datetime import datetime
        output_data = {
            'check_date': datetime.now().isoformat(),
            'summary': {
                'total_moved': result['total_moved'],
                'total_uploaded': result['total_uploaded'],
                'unuploaded_count': result['unuploaded_count'],
                'not_found_count': result['not_found_count'],
            },
            'unuploaded_videos': result['unuploaded_videos']
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"")
        logger.info(f"Results saved to: {output_path}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")


if __name__ == '__main__':
    import argparse

    from utils import paths

    parser = argparse.ArgumentParser(
        description='Check which moved videos are not yet uploaded to YouTube'
    )
    parser.add_argument(
        '--moved-log',
        type=str,
        default=str(paths.PROJECT_ROOT.parent / 'VideoMoveTools' / 'moved_videos_log.json'),
        help='Path to moved_videos_log.json'
    )
    parser.add_argument(
        '--uploaded-titles',
        type=str,
        default=str(paths.UPLOADED_FROM_YOUTUBE_PATH),
        help='Path to uploaded_from_youtube.txt'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=str(paths.DATA_DIR / 'unuploaded_videos.json'),
        help='Output JSON file path'
    )

    args = parser.parse_args()

    moved_log_path = os.path.abspath(args.moved_log)
    uploaded_titles_path = os.path.abspath(args.uploaded_titles)
    output_path = os.path.abspath(args.output)
    
    try:
        result = check_unuploaded_videos(moved_log_path, uploaded_titles_path)
        save_result_json(result, output_path)
        
        if result['unuploaded_count'] > 0:
            logger.info("")
            logger.info(f"Found {result['unuploaded_count']} unuploaded videos.")
            sys.exit(1)
        else:
            logger.info("")
            logger.info("All moved videos are uploaded! ✓")
            sys.exit(0)
    except KeyboardInterrupt:
        logger.info("Check interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

