#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTubeから動画を削除するスクリプト

使用方法:
    python delete_video.py <video_id>
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow
import httplib2

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('delete_video.log', encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)

CLIENT_SECRETS_FILE = "client_secrets.json"
YOUTUBE_ADMIN_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__), CLIENT_SECRETS_FILE))


def get_authenticated_service():
    """YouTube APIの認証済みサービスを取得します。"""
    flow = flow_from_clientsecrets(
        CLIENT_SECRETS_FILE,
        scope=YOUTUBE_ADMIN_SCOPE,
        message=MISSING_CLIENT_SECRETS_MESSAGE
    )
    storage = Storage("youtube-admin-oauth2.json")
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        flags = argparser.parse_args()
        credentials = run_flow(flow, storage, flags)
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, http=credentials.authorize(httplib2.Http()))


def delete_video(youtube: build, video_id: str) -> bool:
    """
    YouTubeから動画を削除します。
    
    Args:
        youtube: YouTube APIサービス
        video_id: 削除する動画のID
        
    Returns:
        削除成功時True、失敗時False
    """
    try:
        youtube.videos().delete(id=video_id).execute()
        logger.info(f"Successfully deleted video: {video_id}")
        return True
    except HttpError as e:
        logger.error(f"An HTTP error {e.resp.status} occurred: {e.content}")
        return False
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return False


def get_video_title(youtube: build, video_id: str) -> Optional[str]:
    """
    YouTube API で動画タイトルを取得します。
    """
    try:
        response = youtube.videos().list(part="snippet", id=video_id).execute()
        items = response.get("items", [])
        if items:
            return items[0].get("snippet", {}).get("title", "").strip()
    except Exception as e:
        logger.warning(f"Could not get video title for {video_id}: {e}")
    return None


def remove_from_uploaded_from_youtube(youtube: build, video_id: str) -> bool:
    """
    data/uploaded_from_youtube.txt から該当動画のタイトル行を削除します（title-only 運用用）。
    API でタイトルを取得してから該当行を除去します。
    """
    try:
        title = get_video_title(youtube, video_id)
        if not title:
            logger.warning("Could not get video title; skipping uploaded_from_youtube.txt update")
            return False
        from utils import paths
        path = paths.UPLOADED_FROM_YOUTUBE_PATH
        if not path.exists():
            logger.debug(f"uploaded_from_youtube.txt not found: {path}")
            return False
        with open(path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        lines = [line for line in all_lines if line.rstrip("\n\r") != title]
        if len(lines) == len(all_lines):
            logger.warning(f"Title not found in uploaded_from_youtube.txt: {title}")
            return False
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        logger.info(f"Removed from uploaded_from_youtube.txt: {title}")
        return True
    except Exception as e:
        logger.error(f"Failed to update uploaded_from_youtube.txt: {e}")
        return False


def delete_local_file(file_path: str) -> bool:
    """
    ローカルファイルを削除します。
    
    Args:
        file_path: 削除するファイルのパス
        
    Returns:
        削除成功時True、失敗時False
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted local file: {file_path}")
            return True
        else:
            logger.warning(f"File not found: {file_path}")
            return False
    except Exception as e:
        logger.error(f"An error occurred while deleting local file: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python delete_video.py <video_id> [--delete-local] [--file-path FILE_PATH]")
        print("  --delete-local: Also delete the local file")
        print("  --file-path: Path to the local file to delete")
        sys.exit(1)
    
    video_id = sys.argv[1]
    delete_local = '--delete-local' in sys.argv
    file_path = None
    
    if '--file-path' in sys.argv:
        idx = sys.argv.index('--file-path')
        if idx + 1 < len(sys.argv):
            file_path = sys.argv[idx + 1]
    
    logger.info(f"Deleting video: {video_id}")
    
    # YouTubeから削除
    youtube = get_authenticated_service()
    if delete_video(youtube, video_id):
        logger.info("✓ Successfully deleted from YouTube")
    else:
        logger.error("✗ Failed to delete from YouTube")
        sys.exit(1)
    
    # data/uploaded_from_youtube.txt から該当タイトル行を削除
    if remove_from_uploaded_from_youtube(youtube, video_id):
        logger.info("✓ Successfully removed from uploaded_from_youtube.txt")
    else:
        logger.warning("⚠ Could not update uploaded_from_youtube.txt (title not found or file missing)")
    
    # ローカルファイルを削除
    if delete_local and file_path:
        if delete_local_file(file_path):
            logger.info("✓ Successfully deleted local file")
        else:
            logger.warning("⚠ Could not delete local file")
    
    logger.info("Deletion process completed")


if __name__ == '__main__':
    main()

