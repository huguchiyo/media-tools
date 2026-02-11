#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube動画アップロード処理ユーティリティ

動画のアップロード処理とリジューム機能を提供します。
"""

import http.client
import httplib2
import random
import time
import logging
from typing import Optional, List
from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

# リトライ設定
httplib2.RETRIES = 1
MAX_RETRIES = 10
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error, IOError, http.client.NotConnected,
    http.client.IncompleteRead, http.client.ImproperConnectionState,
    http.client.CannotSendRequest, http.client.CannotSendHeader,
    http.client.ResponseNotReady, http.client.BadStatusLine
)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def initialize_upload(
    youtube: build,
    title: str,
    file_path: str,
    description: str,
    privacy_status: str = "private",
    category_id: str = "22",
    tags: Optional[List[str]] = None
) -> Optional[str]:
    """
    動画のアップロードを初期化します。
    
    Args:
        youtube: YouTube APIサービス
        title: 動画のタイトル
        file_path: アップロードする動画ファイルのパス
        description: 動画の説明
        privacy_status: プライバシー設定（public, private, unlisted）
        category_id: カテゴリID
        tags: タグのリスト
        
    Returns:
        アップロード成功時は動画ID、失敗時はNone
    """
    if privacy_status not in VALID_PRIVACY_STATUSES:
        raise ValueError(f"Invalid privacy status: {privacy_status}")

    body = dict(
        snippet=dict(
            title=title,
            description=description,
            tags=tags,
            categoryId=category_id
        ),
        status=dict(
            privacyStatus=privacy_status
        )
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(list(body.keys())),
        body=body,
        # Setting "chunksize" equal to -1 means that the entire
        # file will be uploaded in a single HTTP request.
        media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
    )

    return resumable_upload(insert_request)


def resumable_upload(insert_request) -> Optional[str]:
    """
    リジューム可能なアップロードを実行します。
    指数バックオフ戦略を使用してリトライします。
    
    Args:
        insert_request: YouTube APIのinsertリクエスト
        
    Returns:
        アップロード成功時は動画ID、失敗時はNone
    """
    response = None
    error = None
    retry = 0
    
    while response is None:
        try:
            logger.info("Uploading file...")
            status, response = insert_request.next_chunk()
            
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"Upload progress: {progress}%")
            
            if response is not None:
                if 'id' in response:
                    video_id = response['id']
                    logger.info(f"Video id '{video_id}' was successfully uploaded.")
                    # ログを即座に書き込む
                    for handler in logger.handlers:
                        handler.flush()
                    return video_id
                else:
                    logger.error(f"The upload failed with an unexpected response: {response}")
                    return None
                    
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"
            else:
                logger.error(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
                raise

        except RETRIABLE_EXCEPTIONS as e:
            error = f"A retriable error occurred: {e}"

        if error is not None:
            logger.warning(error)
            retry += 1
            if retry > MAX_RETRIES:
                logger.error("No longer attempting to retry.")
                return None

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            logger.info(f"Sleeping {sleep_seconds:.2f} seconds and then retrying...")
            time.sleep(sleep_seconds)
            error = None
    
    return None

