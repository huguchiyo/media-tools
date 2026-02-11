#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存フォルダに写真をマージするスクリプト

既存のフォルダ（例: camera）に、別のフォルダ（例: iPhone_Michino）の内容をマージします。
既存のファイルは保持され、新しいファイルのみ追加されます。

使用方法:
    python merge_into_existing.py <source_folder> <target_folder> [--dry-run] [--execute]
"""

import os
import shutil
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def get_file_info(folder_path):
    """フォルダ内の全ファイル情報を取得"""
    files_info = defaultdict(list)
    
    if not folder_path.exists():
        return files_info
    
    for date_folder in folder_path.iterdir():
        if not date_folder.is_dir():
            continue
        
        date_str = date_folder.name
        
        for file_path in date_folder.iterdir():
            if file_path.is_file():
                file_stem = file_path.stem
                file_ext = file_path.suffix.upper()
                file_size = file_path.stat().st_size
                
                files_info[date_str].append({
                    'stem': file_stem,
                    'filename': file_path.name,
                    'path': file_path,
                    'size': file_size,
                    'ext': file_ext
                })
    
    return files_info

def merge_into_existing(source_folder_name, target_folder_name, dry_run=True):
    """
    既存フォルダに写真をマージします
    
    Args:
        source_folder_name: マージ元フォルダ名（例: iPhone_Michino）
        target_folder_name: マージ先フォルダ名（既存、例: camera）
        dry_run: Trueの場合は実際にはコピーせず、何をするか表示するだけ
    """
    SOURCE_FOLDER = Path(source_folder_name)
    TARGET_FOLDER = Path(target_folder_name)
    
    print("=" * 80)
    print("既存フォルダへの写真マージスクリプト")
    print(f"マージ元: {SOURCE_FOLDER}")
    print(f"マージ先（既存）: {TARGET_FOLDER}")
    print(f"実行モード: {'DRY RUN（実際にはコピーしません）' if dry_run else '実際にコピーします'}")
    print("=" * 80)
    print()
    
    # マージ先フォルダの存在確認
    if not TARGET_FOLDER.exists():
        print(f"エラー: マージ先フォルダが見つかりません: {TARGET_FOLDER}")
        return
    
    # ファイル情報を取得
    print("ファイル情報を収集中...")
    source_files = get_file_info(SOURCE_FOLDER)
    target_files = get_file_info(TARGET_FOLDER)
    
    all_dates = set(source_files.keys()) | set(target_files.keys())
    
    # 統計
    stats = {
        'copied': 0,
        'skipped_exact_duplicate': 0,
        'skipped_jpg_when_heic_exists': 0,
        'skipped_already_exists': 0,
        'deleted_jpg_for_heic': 0, # HEIC優先でJPGを削除
        'errors': []
    }
    
    # 同じstemで複数の拡張子がある場合、HEICを優先
    def select_best_file(files_list):
        """同じstemで複数のファイルがある場合、HEICを優先して選択"""
        files_by_stem = defaultdict(list)
        for f in files_list:
            files_by_stem[f['stem']].append(f)
        
        result = {}
        for stem, file_list in files_by_stem.items():
            # HEICがあればHEICを優先、なければ最初のファイル
            heic_files = [f for f in file_list if f['ext'] == '.HEIC']
            if heic_files:
                result[stem] = heic_files[0]
            else:
                result[stem] = file_list[0]
        return result
    
    # 日付フォルダごとに処理
    for date_str in sorted(all_dates):
        source_files_in_date = select_best_file(source_files.get(date_str, []))
        target_files_in_date = select_best_file(target_files.get(date_str, []))
        
        # マージ先にのみ存在するファイルはそのまま（何もしない）
        # マージ元にのみ存在するファイル、または両方に存在するファイルを処理
        
        # 日付フォルダを作成（存在しない場合）
        target_date_folder = TARGET_FOLDER / date_str
        if not dry_run:
            target_date_folder.mkdir(exist_ok=True)
        
        # マージ元のファイルを処理
        for stem, source_file in source_files_in_date.items():
            target_file = target_files_in_date.get(stem)
            
            if target_file:
                # 両方に存在
                source_ext = source_file['ext']
                target_ext = target_file['ext']
                
                if source_ext == target_ext:
                    # 同じ拡張子
                    if source_file['size'] == target_file['size']:
                        # 完全に同一ファイル（スキップ）
                        stats['skipped_exact_duplicate'] += 1
                        if dry_run:
                            print(f"  [スキップ] 完全に同一ファイル: {date_str}/{source_file['filename']}")
                    else:
                        # サイズが異なる（マージ元をコピー、名前を変更）
                        new_name = f"{source_file['stem']}_from_source{source_file['ext']}"
                        dest_file = target_date_folder / new_name
                        
                        if not dry_run:
                            try:
                                if not dest_file.exists():
                                    shutil.copy2(source_file['path'], dest_file)
                                    stats['copied'] += 1
                                    print(f"  [コピー] {source_file['filename']} -> {new_name} (サイズが異なる)")
                                else:
                                    stats['skipped_already_exists'] += 1
                            except Exception as e:
                                stats['errors'].append(f"エラー: {source_file['path']} -> {dest_file}: {e}")
                        else:
                            stats['copied'] += 1
                            print(f"  [コピー予定] {source_file['filename']} -> {new_name} (サイズが異なる)")
                else:
                    # 異なる拡張子（HEIC vs JPGなど）
                    # HEICを優先
                    if source_ext == '.HEIC' and target_ext != '.HEIC':
                        # マージ元がHEIC、マージ先がJPG → HEICで置き換え、JPGを削除
                        dest_file = target_date_folder / source_file['filename']
                        jpg_to_delete = target_date_folder / target_file['filename']
                        
                        if not dry_run:
                            try:
                                # 既存のJPGファイルを削除
                                if jpg_to_delete.exists():
                                    os.remove(jpg_to_delete)
                                    stats['deleted_jpg_for_heic'] += 1
                                    print(f"  [削除] {target_file['filename']} (HEIC優先のため)")
                                
                                # HEICファイルをコピー
                                if not dest_file.exists():
                                    shutil.copy2(source_file['path'], dest_file)
                                    stats['copied'] += 1
                                    print(f"  [コピー] {source_file['filename']} (HEIC優先)")
                                else:
                                    stats['skipped_already_exists'] += 1
                            except Exception as e:
                                stats['errors'].append(f"エラー: {source_file['path']} -> {dest_file}: {e}")
                        else:
                            stats['copied'] += 1
                            stats['deleted_jpg_for_heic'] += 1
                            print(f"  [削除予定] {target_file['filename']} (HEIC優先のため)")
                            print(f"  [コピー予定] {source_file['filename']} (HEIC優先)")
                    elif target_ext == '.HEIC' and source_ext != '.HEIC':
                        # マージ先がHEIC、マージ元がJPG → スキップ
                        stats['skipped_jpg_when_heic_exists'] += 1
                        if dry_run:
                            print(f"  [スキップ] {source_file['filename']} (マージ先にHEICが存在)")
                    else:
                        # その他の組み合わせ（両方JPGなど）→ マージ元をコピー（名前を変更）
                        new_name = f"{source_file['stem']}_from_source{source_file['ext']}"
                        dest_file = target_date_folder / new_name
                        if not dry_run:
                            try:
                                if not dest_file.exists():
                                    shutil.copy2(source_file['path'], dest_file)
                                    stats['copied'] += 1
                                    print(f"  [コピー] {source_file['filename']} -> {new_name}")
                                else:
                                    stats['skipped_already_exists'] += 1
                            except Exception as e:
                                stats['errors'].append(f"エラー: {source_file['path']} -> {dest_file}: {e}")
                        else:
                            stats['copied'] += 1
                            print(f"  [コピー予定] {source_file['filename']} -> {new_name}")
            else:
                # マージ元にのみ存在（コピー）
                dest_file = target_date_folder / source_file['filename']
                if not dry_run:
                    try:
                        if not dest_file.exists():
                            shutil.copy2(source_file['path'], dest_file)
                            stats['copied'] += 1
                            if stats['copied'] % 100 == 0:
                                print(f"  [コピー中] {stats['copied']}件...")
                        else:
                            stats['skipped_already_exists'] += 1
                    except Exception as e:
                        stats['errors'].append(f"エラー: {source_file['path']} -> {dest_file}: {e}")
                else:
                    stats['copied'] += 1
                    if stats['copied'] % 100 == 0:
                        print(f"  [コピー予定] {stats['copied']}件...")
    
    # 年フォルダも処理（マージ元にある場合）
    print()
    print("年フォルダを処理中...")
    for year_folder in SOURCE_FOLDER.iterdir():
        if year_folder.is_dir() and year_folder.name.isdigit() and len(year_folder.name) == 4:
            # 年フォルダ（例: 2023, 2024, 2025）
            target_year_folder = TARGET_FOLDER / year_folder.name
            if not dry_run:
                target_year_folder.mkdir(exist_ok=True)
            
            for file_path in year_folder.iterdir():
                if file_path.is_file():
                    dest_file = target_year_folder / file_path.name
                    if not dry_run:
                        try:
                            if not dest_file.exists():
                                shutil.copy2(file_path, dest_file)
                                stats['copied'] += 1
                        except Exception as e:
                            stats['errors'].append(f"エラー: {file_path} -> {dest_file}: {e}")
                    else:
                        stats['copied'] += 1
    
    # 統計を表示
    print()
    print("=" * 80)
    print("マージ結果")
    print("=" * 80)
    print(f"コピーしたファイル: {stats['copied']}件")
    print(f"スキップ（完全に同一）: {stats['skipped_exact_duplicate']}件")
    print(f"スキップ（HEIC優先）: {stats['skipped_jpg_when_heic_exists']}件")
    print(f"スキップ（既に存在）: {stats['skipped_already_exists']}件")
    print(f"削除（HEIC優先でJPG削除）: {stats['deleted_jpg_for_heic']}件")
    
    if stats['errors']:
        print(f"\nエラー: {len(stats['errors'])}件")
        for error in stats['errors'][:10]:  # 最初の10件のみ表示
            print(f"  {error}")
        if len(stats['errors']) > 10:
            print(f"  ... 他 {len(stats['errors']) - 10}件のエラー")
    
    print()
    if dry_run:
        print("※ これはDRY RUNです。実際にコピーするには --execute オプションを指定してください。")
    else:
        print("マージが完了しました。")

def main():
    if len(sys.argv) < 3:
        print("使用方法:")
        print("  python merge_into_existing.py <source_folder> <target_folder> [--dry-run] [--execute]")
        print()
        print("例:")
        print("  python merge_into_existing.py iPhone_Michino camera --dry-run")
        print("  python merge_into_existing.py iPhone_Michino camera --execute")
        sys.exit(1)
    
    source_folder = sys.argv[1]
    target_folder = sys.argv[2]
    
    # オプションの確認
    dry_run = True  # デフォルトはDRY RUN
    if '--execute' in sys.argv:
        dry_run = False
    elif '--dry-run' in sys.argv:
        dry_run = True
    
    merge_into_existing(source_folder, target_folder, dry_run=dry_run)

if __name__ == '__main__':
    main()

