#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube API認証ユーティリティ

OAuth 2.0認証を使用してYouTube APIサービスを取得します。
"""

import os
import httplib2
from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

# OAuth 2.0スコープ
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_ADMIN_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"

# API設定
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# クライアントシークレットファイル
CLIENT_SECRETS_FILE = "client_secrets.json"

MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__), '..', CLIENT_SECRETS_FILE))


def get_authenticated_service(args=None, scope: str = YOUTUBE_UPLOAD_SCOPE) -> build:
    """
    YouTube APIの認証済みサービスを取得します。
    
    Args:
        args: コマンドライン引数
        scope: OAuth 2.0スコープ（デフォルトはアップロード用、再生リスト操作にはYOUTUBE_ADMIN_SCOPEが必要）
        
    Returns:
        認証済みのYouTube APIサービス
    """
    flow = flow_from_clientsecrets(
        os.path.join(os.path.dirname(__file__), '..', CLIENT_SECRETS_FILE),
        scope=scope,
        message=MISSING_CLIENT_SECRETS_MESSAGE
    )

    storage = Storage(os.path.join(os.path.dirname(__file__), '..', "youtube-admin-oauth2.json"))
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        if args is None:
            args = argparser.parse_args()
        credentials = run_flow(flow, storage, args)

    return build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http())
    )

