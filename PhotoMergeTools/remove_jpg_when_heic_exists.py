#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HEIC vs JPGの重複で、HEICが優先された場合にJPGファイルを削除するスクリプト

cameraフォルダ内で、同じstemでHEICとJPGの両方が存在する場合、JPGを削除します。

使用方法:
    python remove_jpg_when_heic_exists.py <target_folder> [--execute]
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import argparse

def find_heic_jpg_duplicates(target_folder: str) -> list:
    """
    target_folder内で、同じstemでHEICとJPGの両方が存在するファイルを探します。
    
    Returns:
        [(date_folder, filename_stem), ...] のリスト
    """
    TARGET_FOLDER = Path(target_folder)
    
    if not TARGET_FOLDER.exists():
        print(f"エラー: 対象フォルダが見つかりません: {TARGET_FOLDER}")
        return []
    
    duplicates = []
    
    # 日付フォルダごとに処理
    for date_folder in TARGET_FOLDER.iterdir():
        if not date_folder.is_dir():
            continue
        
        date_str = date_folder.name
        
        # ファイルをstemごとにグループ化
        files_by_stem = defaultdict(dict)
        
        for file_path in date_folder.iterdir():
            if not file_path.is_file():
                continue
            
            stem = file_path.stem
            ext = file_path.suffix.upper()
            
            if ext in ['.HEIC', '.JPG', '.JPEG']:
                files_by_stem[stem][ext] = file_path
        
        # HEICとJPGの両方が存在するstemを探す
        for stem, files in files_by_stem.items():
            has_heic = '.HEIC' in files
            has_jpg = '.JPG' in files or '.JPEG' in files
            
            if has_heic and has_jpg:
                duplicates.append((date_str, stem))
    
    return duplicates

def remove_jpg_files(target_folder: str, duplicates: list, dry_run: bool = True) -> None:
    """
    HEIC vs JPGの重複で、HEICが優先された場合にJPGファイルを削除します。
    """
    TARGET_FOLDER = Path(target_folder)
    
    print("=" * 80)
    print("HEIC優先時のJPGファイル削除スクリプト")
    print(f"対象フォルダ: {TARGET_FOLDER}")
    print(f"重複件数: {len(duplicates)}件")
    print(f"実行モード: {'DRY RUN（実際には削除しません）' if dry_run else '実際に削除します'}")
    print("=" * 80)
    print()
    
    if not TARGET_FOLDER.exists():
        print(f"エラー: 対象フォルダが見つかりません: {TARGET_FOLDER}")
        return
    
    deleted_count = 0
    not_found_count = 0
    heic_not_found_count = 0
    errors = []
    
    for date_folder, filename_stem in duplicates:
        jpg_path = TARGET_FOLDER / date_folder / f"{filename_stem}.JPG"
        jpeg_path = TARGET_FOLDER / date_folder / f"{filename_stem}.JPEG"
        heic_path = TARGET_FOLDER / date_folder / f"{filename_stem}.HEIC"
        
        # HEICファイルが存在することを確認
        if not heic_path.exists():
            heic_not_found_count += 1
            if not dry_run:
                print(f"  [警告] HEICファイルが見つかりません: {heic_path}")
            continue
        
        # JPGまたはJPEGファイルを削除
        jpg_to_delete = None
        if jpg_path.exists():
            jpg_to_delete = jpg_path
        elif jpeg_path.exists():
            jpg_to_delete = jpeg_path
        
        if not jpg_to_delete:
            not_found_count += 1
            continue
        
        # JPGファイルを削除
        if dry_run:
            print(f"  [削除予定] {date_folder}/{jpg_to_delete.name}")
            deleted_count += 1
        else:
            try:
                os.remove(jpg_to_delete)
                print(f"  [削除済み] {date_folder}/{jpg_to_delete.name}")
                deleted_count += 1
            except OSError as e:
                errors.append(f"エラー: {jpg_to_delete}: {e}")
                print(f"  [エラー] 削除できませんでした {date_folder}/{jpg_to_delete.name}: {e}")
    
    print()
    print("=" * 80)
    print("削除結果")
    print(f"削除した/削除予定のJPGファイル: {deleted_count}件")
    if not_found_count > 0:
        print(f"JPGファイルが見つからなかった: {not_found_count}件")
    if heic_not_found_count > 0:
        print(f"HEICファイルが見つからなかった: {heic_not_found_count}件")
    if errors:
        print(f"エラー数: {len(errors)}件")
        for error in errors[:10]:
            print(f"  {error}")
        if len(errors) > 10:
            print(f"  ... 他 {len(errors) - 10} 件のエラー")
    print("=" * 80)
    
    if dry_run:
        print("\nこれはDRY RUNです。実際には削除していません。")
        print(f"実際に削除するには: python {Path(__file__).name} <target_folder> --execute")
    else:
        print("\n削除が完了しました。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Remove JPG files when HEIC files exist (HEIC priority).')
    parser.add_argument('target_folder', type=str, help='The target folder to search and delete JPG files from (e.g., camera)')
    parser.add_argument('--execute', action='store_true', help='Execute the deletion operation (default is dry-run)')
    
    args = parser.parse_args()
    
    duplicates = find_heic_jpg_duplicates(args.target_folder)
    if duplicates:
        print(f"HEICとJPGの両方が存在するファイル: {len(duplicates)}件見つかりました")
        remove_jpg_files(args.target_folder, duplicates, dry_run=not args.execute)
    else:
        print("削除対象のファイルが見つかりませんでした。")
