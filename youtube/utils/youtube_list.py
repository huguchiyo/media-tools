#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube API リスト操作ユーティリティ

プレイリスト、アップロード済み動画の取得など、YouTube APIのリスト操作を提供します。
"""

import logging
from typing import List, Dict, Any, Optional
from apiclient.discovery import build
from apiclient.errors import HttpError
from . import auth

logger = logging.getLogger(__name__)

# OAuth 2.0スコープ（authモジュールからインポート）
YOUTUBE_ADMIN_SCOPE = auth.YOUTUBE_ADMIN_SCOPE
YOUTUBE_READONLY_SCOPE = auth.YOUTUBE_READONLY_SCOPE


def get_playlists(youtube: build) -> List[Dict[str, Any]]:
    """
    認証済みユーザーのプレイリスト一覧を取得します。
    
    Args:
        youtube: YouTube APIサービス
        
    Returns:
        プレイリストのリスト
    """
    try:
        playlist_response = youtube.playlists().list(
            mine=True,
            part="id,snippet",
            maxResults=50
        ).execute()
        
        return playlist_response.get("items", [])
    except HttpError as e:
        logger.error(f"An HTTP error {e.resp.status} occurred while fetching playlists: {e.content}")
        return []
    except Exception as e:
        logger.error(f"An error occurred while fetching playlists: {e}")
        return []


def get_playlist_id(title: str, playlists: List[Dict[str, Any]]) -> Optional[str]:
    """
    タイトルからプレイリストIDを取得します。
    
    Args:
        title: プレイリストのタイトル
        playlists: プレイリストのリスト
        
    Returns:
        プレイリストID、見つからない場合はNone
    """
    for playlist in playlists:
        if title == playlist["snippet"]["title"]:
            return playlist["id"]
    return None


def get_playlist_items(playlist_id: str, youtube: build) -> List[Dict[str, Any]]:
    """
    プレイリスト内のアイテムを取得します。
    
    Args:
        playlist_id: プレイリストID
        youtube: YouTube APIサービス
        
    Returns:
        プレイリストアイテムのリスト
    """
    try:
        all_playlist_items = []
        playlist_item_request = youtube.playlistItems().list(
            playlistId=playlist_id,
            part="id,snippet,contentDetails",
            maxResults=50
        )
        
        while playlist_item_request:
            playlist_item_response = playlist_item_request.execute()
            all_playlist_items.extend(playlist_item_response.get("items", []))
            playlist_item_request = youtube.playlistItems().list_next(
                playlist_item_request, playlist_item_response
            )
        
        return all_playlist_items
    except HttpError as e:
        logger.error(f"An HTTP error {e.resp.status} occurred while fetching playlist items: {e.content}")
        return []
    except Exception as e:
        logger.error(f"An error occurred while fetching playlist items: {e}")
        return []


def get_upload_titles(youtube: Optional[build] = None, scope: str = YOUTUBE_READONLY_SCOPE) -> List[Dict[str, Any]]:
    """
    アップロード済み動画のタイトルリストを取得します。
    
    Args:
        youtube: YouTube APIサービス（Noneの場合は新規取得）
        scope: OAuth 2.0スコープ
        
    Returns:
        アップロード済み動画のリスト
    """
    try:
        if youtube is None:
            youtube = auth.get_authenticated_service(scope=scope)
        
        channels_response = youtube.channels().list(
            mine=True,
            part="contentDetails"
        ).execute()
        
        playlist_items = []
        
        for channel in channels_response.get("items", []):
            # アップロード済み動画のプレイリストIDを取得
            uploads_list_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
            logger.info(f"Videos in list {uploads_list_id}")
            playlist_items = get_playlist_items(uploads_list_id, youtube)
        
        # タイトル順にソート
        playlist_items = sorted(playlist_items, key=lambda x: x['snippet']['title'])
        
        return playlist_items
    except HttpError as e:
        logger.error(f"An HTTP error {e.resp.status} occurred while fetching upload titles: {e.content}")
        return []
    except Exception as e:
        logger.error(f"An error occurred while fetching upload titles: {e}")
        return []


def delete_playlist_item(playlist_item_id: str, youtube: build) -> bool:
    """
    プレイリストからアイテムを削除します。

    Args:
        playlist_item_id: 削除するプレイリストアイテムのID（動画IDではなく playlistItem の id）
        youtube: YouTube APIサービス

    Returns:
        削除成功時True、失敗時False
    """
    try:
        youtube.playlistItems().delete(id=playlist_item_id).execute()
        logger.info(f"Deleted playlist item: {playlist_item_id}")
        return True
    except HttpError as e:
        logger.error(f"An HTTP error {e.resp.status} occurred while deleting playlist item: {e.content}")
        return False
    except Exception as e:
        logger.error(f"An error occurred while deleting playlist item: {e}")
        return False


def update_playlist_item(playlist_item: Dict[str, Any], youtube: build) -> bool:
    """
    プレイリストアイテムを更新します。
    
    Args:
        playlist_item: 更新するプレイリストアイテム
        youtube: YouTube APIサービス
        
    Returns:
        更新成功時True、失敗時False
    """
    try:
        youtube.playlistItems().update(
            part="snippet",
            body=dict(
                id=playlist_item['id'],
                snippet=playlist_item['snippet']
            )
        ).execute()
        logger.info(f"Updated playlist item: {playlist_item['snippet']['title']}")
        return True
    except HttpError as e:
        logger.error(f"An HTTP error {e.resp.status} occurred while updating playlist item: {e.content}")
        return False
    except Exception as e:
        logger.error(f"An error occurred while updating playlist item: {e}")
        return False


def get_youtube_service(scope: str = YOUTUBE_ADMIN_SCOPE) -> build:
    """
    YouTube APIサービスを取得します（認証済み）。
    
    Args:
        scope: OAuth 2.0スコープ
        
    Returns:
        認証済みのYouTube APIサービス
    """
    return auth.get_authenticated_service(scope=scope)

