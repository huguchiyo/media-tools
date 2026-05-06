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
from pathlib import Path
from typing import Optional, List
from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)


class MissingLocationHeaderError(Exception):
    """Resumable upload response misses Location header."""
    pass

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
VALID_UPLOAD_MODES = ("simple", "resumable", "auto")
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB


def initialize_upload(
    youtube: build,
    title: str,
    file_path: str,
    description: str,
    privacy_status: str = "private",
    category_id: str = "22",
    tags: Optional[List[str]] = None,
    upload_mode: str = "simple",
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
    if upload_mode not in VALID_UPLOAD_MODES:
        raise ValueError(f"Invalid upload mode: {upload_mode}")

    file_size = Path(file_path).stat().st_size
    logger.info(
        "Preparing upload: mode=%s, file=%s, size=%.2f MB, chunk_size=%.2f MB",
        upload_mode,
        file_path,
        file_size / (1024 * 1024),
        UPLOAD_CHUNK_SIZE / (1024 * 1024),
    )

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

    if upload_mode == "simple":
        return simple_upload(youtube, body, file_path, reason="configured simple mode")

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(list(body.keys())),
        body=body,
        # 小さめチャンクで送ることで、ネットワークが不安定な環境でも
        # タイムアウト時に途中から再試行しやすくする。
        media_body=MediaFileUpload(file_path, chunksize=UPLOAD_CHUNK_SIZE, resumable=True)
    )

    if upload_mode == "resumable":
        return resumable_upload(insert_request, fallback_on_missing_location=False)

    try:
        return resumable_upload(insert_request, fallback_on_missing_location=True)
    except MissingLocationHeaderError as e:
        logger.warning(
            "Resumable upload failed due to missing Location header. "
            "Falling back to non-resumable upload. detail=%s",
            e,
        )
        return simple_upload(youtube, body, file_path, reason="auto fallback after missing Location header")


def simple_upload(youtube: build, body: dict, file_path: str, reason: str = "simple upload") -> Optional[str]:
    """
    非リジュームで単発アップロードする。
    リジューム応答の相性問題（Locationヘッダ欠落）時のフォールバック用。
    """
    request = youtube.videos().insert(
        part=",".join(list(body.keys())),
        body=body,
        media_body=MediaFileUpload(file_path, resumable=False),
    )
    try:
        logger.info("Uploading file (non-resumable: %s)...", reason)
        response = request.execute()
        if response and "id" in response:
            video_id = response["id"]
            logger.info("Video id '%s' was successfully uploaded.", video_id)
            return video_id
        logger.error("The upload failed with an unexpected response: %s", response)
        return None
    except HttpError as e:
        logger.error("Non-resumable upload failed with HTTP %s:\n%s", e.resp.status, e.content)
        raise
    except Exception as e:
        logger.error("Non-resumable upload failed: %s", e)
        return None


def resumable_upload(insert_request, fallback_on_missing_location: bool = False) -> Optional[str]:
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
            message = str(e)
            if "missing a Location" in message:
                # 一部環境でリジュームアップロード時に発生する既知の相性問題。
                if fallback_on_missing_location:
                    raise MissingLocationHeaderError(message)
                logger.error(
                    "Resumable upload cannot continue because the response is missing "
                    "a Location header. Try upload_mode=simple or upload_mode=auto."
                )
                return None
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

