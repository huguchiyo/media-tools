#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OAuth 2.0 トークンファイルを削除するスクリプト。

403 Insufficient Permission（スコープ不足）が出たときに実行すると、
次回のアップロードや API 実行時にブラウザで再ログインし、
必要な権限（アップロードなど）をあらためて許可できます。

使い方:
    python clear_oauth_token.py
"""

import os
import sys
from pathlib import Path

TOKEN_FILE = "youtube-admin-oauth2.json"


def main():
    script_dir = Path(__file__).resolve().parent
    token_path = script_dir / TOKEN_FILE

    if not token_path.exists():
        print(f"Token file not found: {token_path}")
        print("Nothing to delete.")
        return 0

    try:
        token_path.unlink()
        print(f"Deleted: {token_path}")
        print("Next time you run upload or API, you will be asked to sign in again.")
        return 0
    except OSError as e:
        print(f"Failed to delete: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
