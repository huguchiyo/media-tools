#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_from_source が付いたファイルを削除するスクリプト

使用方法:
    python remove_from_source_files.py <target_folder> [--dry-run] [--execute]
"""

import os
import sys
from pathlib import Path

def remove_from_source_files(target_folder_name, dry_run=True):
    """
    _from_source が付いたファイルを削除します
    
    Args:
        target_folder_name: 対象フォルダ名（例: camera）
        dry_run: Trueの場合は実際には削除せず、何を削除するか表示するだけ
    """
    TARGET_FOLDER = Path(target_folder_name)
    
    print("=" * 80)
    print("_from_source ファイル削除スクリプト")
    print(f"対象フォルダ: {TARGET_FOLDER}")
    print(f"実行モード: {'DRY RUN（実際には削除しません）' if dry_run else '実際に削除します'}")
    print("=" * 80)
    print()
    
    if not TARGET_FOLDER.exists():
        print(f"エラー: 対象フォルダが見つかりません: {TARGET_FOLDER}")
        return
    
    # _from_source が付いたファイルを検索
    print("_from_source が付いたファイルを検索中...")
    files_to_delete = []
    
    for file_path in TARGET_FOLDER.rglob("*_from_source*"):
        if file_path.is_file():
            files_to_delete.append(file_path)
    
    if not files_to_delete:
        print("_from_source が付いたファイルは見つかりませんでした。")
        return
    
    print(f"見つかったファイル: {len(files_to_delete)}件")
    print()
    
    # 削除実行
    deleted_count = 0
    error_count = 0
    
    for file_path in files_to_delete:
        relative_path = file_path.relative_to(TARGET_FOLDER)
        
        if not dry_run:
            try:
                file_path.unlink()
                deleted_count += 1
                if deleted_count % 10 == 0:
                    print(f"  [削除中] {deleted_count}件...")
            except Exception as e:
                error_count += 1
                print(f"  [エラー] {relative_path}: {e}")
        else:
            print(f"  [削除予定] {relative_path}")
    
    # 統計を表示
    print()
    print("=" * 80)
    print("削除結果")
    print("=" * 80)
    if dry_run:
        print(f"削除予定ファイル: {len(files_to_delete)}件")
        print()
        print("※ これはDRY RUNです。実際に削除するには --execute オプションを指定してください。")
    else:
        print(f"削除したファイル: {deleted_count}件")
        if error_count > 0:
            print(f"エラー: {error_count}件")
        print()
        print("削除が完了しました。")

def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python remove_from_source_files.py <target_folder> [--dry-run] [--execute]")
        print()
        print("例:")
        print("  python remove_from_source_files.py camera --dry-run")
        print("  python remove_from_source_files.py camera --execute")
        sys.exit(1)
    
    target_folder = sys.argv[1]
    
    # オプションの確認
    dry_run = True  # デフォルトはDRY RUN
    if '--execute' in sys.argv:
        dry_run = False
    elif '--dry-run' in sys.argv:
        dry_run = True
    
    remove_from_source_files(target_folder, dry_run=dry_run)

if __name__ == '__main__':
    main()

