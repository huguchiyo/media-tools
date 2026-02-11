#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTubeプレイリスト操作ユーティリティ

プレイリストの作成、動画の追加、ソートなどの操作を提供します。
"""

import re
import logging
from typing import Optional
from apiclient.discovery import build
from apiclient.errors import HttpError
from . import youtube_list

logger = logging.getLogger(__name__)


def create_or_get_playlist(year: str, youtube: build) -> Optional[str]:
    """
    年ごとの再生リストを作成または取得します。
    
    Args:
        year: 年（例：2025）
        youtube: YouTube APIサービス
        
    Returns:
        プレイリストID、失敗時はNone
    """
    try:
        # 既存のプレイリストを検索
        playlists = youtube_list.get_playlists(youtube)
        playlist_id = youtube_list.get_playlist_id(year, playlists)
        
        if playlist_id:
            logger.info(f"Found existing playlist: {year} (ID: {playlist_id})")
            return playlist_id
        
        # プレイリストが存在しない場合は作成
        logger.info(f"Creating new playlist: {year}")
        playlist_response = youtube.playlists().insert(
            part="snippet,status",
            body=dict(
                snippet=dict(
                    title=year,
                    description=f"{year}年の動画"
                ),
                status=dict(
                    privacyStatus="private"
                )
            )
        ).execute()
        
        playlist_id = playlist_response["id"]
        logger.info(f"Created playlist: {year} (ID: {playlist_id})")
        return playlist_id
        
    except HttpError as e:
        logger.error(f"An HTTP error {e.resp.status} occurred while creating/getting playlist: {e.content}")
        return None
    except Exception as e:
        logger.error(f"An error occurred while creating/getting playlist: {e}")
        return None


def add_video_to_playlist(video_id: str, playlist_id: str, youtube: build) -> bool:
    """
    動画を再生リストに追加します（重複チェック付き）。
    
    Args:
        video_id: 動画ID
        playlist_id: プレイリストID
        youtube: YouTube APIサービス
        
    Returns:
        追加成功時True、失敗時False
    """
    try:
        # 既にプレイリストに含まれているかチェック
        playlist_items = youtube_list.get_playlist_items(playlist_id, youtube)
        for item in playlist_items:
            if item['snippet']['resourceId']['videoId'] == video_id:
                logger.info(f"Video {video_id} already in playlist, skipping")
                return True
        
        # プレイリストに追加
        response = youtube.playlistItems().insert(
            part="snippet",
            body=dict(
                snippet=dict(
                    playlistId=playlist_id,
                    resourceId=dict(
                        kind="youtube#video",
                        videoId=video_id
                    )
                )
            )
        ).execute()
        
        logger.info(f"Added video {video_id} to playlist {playlist_id}")
        return True
        
    except HttpError as e:
        if e.resp.status == 409:  # 重複エラー
            logger.info(f"Video {video_id} already in playlist (409 error)")
            return True
        logger.error(f"An HTTP error {e.resp.status} occurred while adding video to playlist: {e.content}")
        return False
    except Exception as e:
        logger.error(f"An error occurred while adding video to playlist: {e}")
        return False


def sort_playlist_by_date(playlist_id: str, youtube: build) -> None:
    """
    再生リスト内の動画を撮影日順にソートします。
    ずれている動画だけを正しい位置に差し込むため、必要な API 更新は最小限にします。
    
    Args:
        playlist_id: プレイリストID
        youtube: YouTube APIサービス
    """
    try:
        playlist_items = youtube_list.get_playlist_items(playlist_id, youtube)
        
        # タイトルから撮影日を抽出してソート
        def extract_date_from_title(title: str) -> tuple:
            # タイトル形式: "2025 0102 IMG 0363" または "2025 0102 IMG_0363"
            match = re.match(r'^(\d{4})\s+(\d{4})', title)
            if match:
                year = int(match.group(1))
                month_day = match.group(2)
                month = int(month_day[:2])
                day = int(month_day[2:])
                return (year, month, day)
            # フォールバック: タイトル全体でソート
            return (0, 0, 0)
        
        # 撮影日順の正しい並びを計算
        sorted_items = sorted(playlist_items, key=lambda x: extract_date_from_title(x['snippet']['title']))
        
        # 「現在位置 != あるべき位置」のアイテムだけ列挙（あるべき位置 = sorted での index）
        to_move = []
        for target_pos, item in enumerate(sorted_items):
            current_pos = item['snippet'].get('position', target_pos)
            if current_pos != target_pos:
                to_move.append((current_pos, target_pos, item))
        
        if not to_move:
            logger.info(f"Playlist {playlist_id} is already sorted")
            return
        
        # 現在位置が後ろのものから更新。1件更新すると後続がずれるので「実質もう正しい位置」のものはスキップする
        to_move.sort(key=lambda x: x[0], reverse=True)
        done_moves = []  # (prev_curr, prev_target) のリスト
        actually_moved = 0
        for curr, target_pos, item in to_move:
            # 既に行った更新でこのアイテムがずれた後の「実質の現在位置」
            effective_curr = curr
            for (prev_curr, prev_target) in done_moves:
                if prev_target <= curr < prev_curr:
                    effective_curr += 1
            if effective_curr == target_pos:
                continue  # もう正しい位置にあるのでスキップ
            item['snippet']['position'] = target_pos
            youtube_list.update_playlist_item(item, youtube)
            done_moves.append((curr, target_pos))
            actually_moved += 1
        logger.info(f"Sorting playlist {playlist_id}: moved {actually_moved} item(s) to correct position")
        if actually_moved > 0:
            logger.info(f"Playlist sorted successfully")
            
    except Exception as e:
        logger.error(f"An error occurred while sorting playlist: {e}")


def remove_duplicate_playlist_items(playlist_id: str, youtube: build) -> int:
    """
    再生リスト内の重複動画（同じ videoId が複数回あるもの）を削除する。
    先頭に現れた動画は残し、2回目以降の出現をプレイリストから削除する。

    Args:
        playlist_id: プレイリストID
        youtube: YouTube APIサービス

    Returns:
        削除したアイテム数
    """
    try:
        playlist_items = youtube_list.get_playlist_items(playlist_id, youtube)
        seen_video_ids = set()
        to_delete = []  # (playlist_item_id, title) のリスト
        for item in playlist_items:
            video_id = item["snippet"]["resourceId"]["videoId"]
            title = item["snippet"].get("title", "")
            if video_id in seen_video_ids:
                to_delete.append((item["id"], title))
            else:
                seen_video_ids.add(video_id)

        deleted = 0
        for pl_item_id, title in to_delete:
            if youtube_list.delete_playlist_item(pl_item_id, youtube):
                deleted += 1
                logger.info(f"Removed duplicate from playlist: {title} (item id: {pl_item_id})")
        if to_delete:
            logger.info(f"Removed {deleted} duplicate(s) from playlist {playlist_id}")
        return deleted
    except Exception as e:
        logger.error(f"An error occurred while removing duplicates: {e}")
        return 0

