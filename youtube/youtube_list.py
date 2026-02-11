#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube API リスト操作ユーティリティ（後方互換性のため）

このモジュールはutils/youtube_list.pyを再エクスポートします。
既存のコードとの互換性を保つため、親ディレクトリからもインポート可能にします。
"""

# utils/youtube_list.pyからすべてをインポート
from utils.youtube_list import *
from utils import auth

# 後方互換性のため、スコープもエクスポート
YOUTUBE_ADMIN_SCOPE = auth.YOUTUBE_ADMIN_SCOPE
YOUTUBE_READONLY_SCOPE = auth.YOUTUBE_READONLY_SCOPE

