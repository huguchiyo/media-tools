#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube API認証ユーティリティ

OAuth 2.0認証を使用してYouTube APIサービスを取得します。
"""

import json
import os
from pathlib import Path
from typing import List

from apiclient.discovery import build
import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow

# OAuth 2.0スコープ
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_ADMIN_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"

# API設定
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# クライアントシークレット / トークンファイル
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLIENT_SECRETS_PATH = PROJECT_ROOT / "client_secrets.json"
TOKEN_FILE_PATH = PROJECT_ROOT / "youtube-admin-oauth2.json"
HTTP_TIMEOUT_SECONDS = 120

MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(CLIENT_SECRETS_PATH)


def _normalize_scopes(scope: str) -> List[str]:
    """build / InstalledAppFlow 向けにスコープを配列化する。"""
    if isinstance(scope, str):
        return [scope]
    return list(scope or [])


def _load_saved_credentials(scopes: List[str]):
    """保存済みトークンを読み込む。破損していれば破棄して再認証する。"""
    if not TOKEN_FILE_PATH.exists():
        return None
    try:
        credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE_PATH), scopes=scopes)
    except Exception:
        return None

    granted_scopes = set(credentials.granted_scopes or credentials.scopes or [])
    if scopes and not set(scopes).issubset(granted_scopes):
        return None
    return credentials


def _save_credentials(credentials: Credentials) -> None:
    TOKEN_FILE_PATH.write_text(credentials.to_json(), encoding="utf-8")


def get_authenticated_service(args=None, scope: str = YOUTUBE_UPLOAD_SCOPE) -> build:
    """
    YouTube APIの認証済みサービスを取得します。
    
    Args:
        args: 互換性のため残している未使用引数
        scope: OAuth 2.0スコープ（デフォルトはアップロード用、再生リスト操作にはYOUTUBE_ADMIN_SCOPEが必要）
        
    Returns:
        認証済みのYouTube APIサービス
    """
    del args  # 既存呼び出しとの互換性維持

    if not CLIENT_SECRETS_PATH.exists():
        raise FileNotFoundError(MISSING_CLIENT_SECRETS_MESSAGE)

    scopes = _normalize_scopes(scope)
    credentials = _load_saved_credentials(scopes)

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            _save_credentials(credentials)
        except Exception:
            credentials = None

    if credentials is None or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_PATH), scopes=scopes)
        credentials = flow.run_local_server(
            host="localhost",
            # 固定ポート競合を避けるため、空きポートを自動選択する。
            port=0,
            authorization_prompt_message="Your browser has been opened to visit:\n\n{url}\n",
            success_message="The authentication flow has completed. You may close this window.",
            open_browser=True,
        )
        _save_credentials(credentials)

    return build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        http=AuthorizedHttp(credentials, http=httplib2.Http(timeout=HTTP_TIMEOUT_SECONDS)),
        cache_discovery=False,
    )

