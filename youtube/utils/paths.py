#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
プロジェクト共通のパス定義。

utils/ の親ディレクトリをプロジェクトルートとし、
data/uploaded_from_youtube.txt 等のパスを一箇所で管理する。
"""

from pathlib import Path

# プロジェクトルート（Tools/youtube/）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROJECT_ROOT: Path = _PROJECT_ROOT
DATA_DIR: Path = _PROJECT_ROOT / "data"
LOGS_DIR: Path = _PROJECT_ROOT / "logs"

# アップロード済み一覧（スキップ判定・成功時追記）
UPLOADED_FROM_YOUTUBE_PATH: Path = DATA_DIR / "uploaded_from_youtube.txt"


def ensure_data_dir() -> Path:
    """data/ を存在させて返す。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def ensure_logs_dir() -> Path:
    """logs/ を存在させて返す。"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR
