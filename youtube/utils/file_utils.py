#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ファイル処理ユーティリティ

ファイルのハッシュ値計算、ファイル名処理、動画ファイル判定など。
"""

import re
import hashlib
import os
from pathlib import Path
from typing import Optional

# 動画ファイルの拡張子
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m2ts', '.mts', '.avi', '.mkv', '.wmv', '.flv', '.webm'}


def calculate_file_hash(file_path: str, chunk_size: int = 8192) -> Optional[str]:
    """
    ファイルのMD5ハッシュ値を計算します。
    
    Args:
        file_path: ファイルパス
        chunk_size: チャンクサイズ（メモリ効率のため）
        
    Returns:
        ハッシュ値（16進数文字列）、失敗時はNone
    """
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        return None


def extract_year_from_filename(file_name: str) -> Optional[str]:
    """
    ファイル名から年を抽出します（例：2025_0102_IMG_0363.MOV -> 2025）
    
    Args:
        file_name: ファイル名
        
    Returns:
        年（文字列）、失敗時はNone
    """
    match = re.match(r'^(\d{4})_', file_name)
    if match:
        return match.group(1)
    return None


def extract_year_from_dir_path(dir_path: str) -> Optional[str]:
    """
    ディレクトリパスから年を抽出します（例：movie/2026 -> 2026）
    
    Args:
        dir_path: ディレクトリパス
        
    Returns:
        年（文字列）、失敗時はNone
    """
    # パスを正規化して、最後のディレクトリ名を取得
    normalized_path = os.path.normpath(dir_path)
    dir_name = os.path.basename(normalized_path)
    
    # 4桁の数字（年）を抽出
    match = re.match(r'^(\d{4})$', dir_name)
    if match:
        return match.group(1)
    return None


def modify_movie_name(file_name: str) -> Optional[str]:
    """
    ファイル名から動画タイトルを生成します。
    拡張子を除去し、アンダースコアをスペースに置換します。
    
    Args:
        file_name: ファイル名
        
    Returns:
        生成されたタイトル、失敗時はNone
    """
    # '.' より前だけ抜き出す
    ptn = re.compile(r'(.*)(\.[^.]+$)')
    result = ptn.search(file_name)
    
    if result:
        title = result.group(1)
        # '_' は ' ' に置換する
        return title.replace('_', ' ')
    return None


def is_video_file(file_path: str) -> bool:
    """
    ファイルが動画ファイルかどうかを判定します。
    
    Args:
        file_path: ファイルパス
        
    Returns:
        動画ファイルの場合True
    """
    ext = Path(file_path).suffix.lower()
    return ext in VIDEO_EXTENSIONS

