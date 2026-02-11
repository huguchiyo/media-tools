#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iPhone写真フォルダのマージスクリプト（汎用版）
任意の2つのフォルダをマージできます
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

def merge_photos(folder1_name, folder2_name, output_folder_name, dry_run=True):
    """
    写真をマージします
    
    Args:
        folder1_name: 1つ目のフォルダ名
        folder2_name: 2つ目のフォルダ名
        output_folder_name: マージ先フォルダ名
        dry_run: Trueの場合は実際にはコピーせず、何をするか表示するだけ
    """
    FOLDER1 = Path(folder1_name)
    FOLDER2 = Path(folder2_name)
    OUTPUT_FOLDER = Path(output_folder_name)
    
    print("=" * 80)
    print("iPhone写真フォルダ マージスクリプト")
    print(f"フォルダ1: {FOLDER1}")
    print(f"フォルダ2: {FOLDER2}")
    print(f"マージ先: {OUTPUT_FOLDER}")
    print(f"実行モード: {'DRY RUN（実際にはコピーしません）' if dry_run else '実際にコピーします'}")
    print("=" * 80)
    print()
    
    # ファイル情報を取得
    print("ファイル情報を収集中...")
    files1 = get_file_info(FOLDER1)
    files2 = get_file_info(FOLDER2)
    
    all_dates = set(files1.keys()) | set(files2.keys())
    
    # 統計
    stats = {
        'copied': 0,
        'skipped_exact_duplicate': 0,
        'skipped_jpg_when_heic_exists': 0,
        'errors': []
    }
    
    # マージ先フォルダを作成
    if not dry_run:
        OUTPUT_FOLDER.mkdir(exist_ok=True)
        print(f"マージ先フォルダを作成: {OUTPUT_FOLDER}")
    else:
        print(f"マージ先フォルダ（作成予定）: {OUTPUT_FOLDER}")
    print()
    
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
        files_in_date1 = select_best_file(files1.get(date_str, []))
        files_in_date2 = select_best_file(files2.get(date_str, []))
        
        all_stems = set(files_in_date1.keys()) | set(files_in_date2.keys())
        
        # 日付フォルダを作成
        output_date_folder = OUTPUT_FOLDER / date_str
        if not dry_run:
            output_date_folder.mkdir(exist_ok=True)
        
        for stem in sorted(all_stems):
            file1 = files_in_date1.get(stem)
            file2 = files_in_date2.get(stem)
            
            if file1 and file2:
                # 両方に存在
                ext1 = file1['ext']
                ext2 = file2['ext']
                
                if ext1 == ext2:
                    # 同じ拡張子
                    if file1['size'] == file2['size']:
                        # 完全に同一ファイル（片方だけコピー）
                        source_file = file1['path']  # folder1を優先
                        dest_file = output_date_folder / file1['filename']
                        
                        if not dry_run:
                            try:
                                if not dest_file.exists():
                                    shutil.copy2(source_file, dest_file)
                                    stats['copied'] += 1
                                else:
                                    stats['skipped_exact_duplicate'] += 1
                            except Exception as e:
                                stats['errors'].append(f"エラー: {source_file} -> {dest_file}: {e}")
                        else:
                            stats['copied'] += 1
                            stats['skipped_exact_duplicate'] += 1
                    else:
                        # サイズが異なる（両方コピー、名前を変更）
                        # file1をコピー
                        dest1 = output_date_folder / file1['filename']
                        if not dry_run:
                            try:
                                if not dest1.exists():
                                    shutil.copy2(file1['path'], dest1)
                                    stats['copied'] += 1
                            except Exception as e:
                                stats['errors'].append(f"エラー: {file1['path']} -> {dest1}: {e}")
                        else:
                            stats['copied'] += 1
                        
                        # file2をコピー（名前を変更）
                        new_name2 = f"{file2['stem']}_2{file2['ext']}"
                        dest2 = output_date_folder / new_name2
                        if not dry_run:
                            try:
                                if not dest2.exists():
                                    shutil.copy2(file2['path'], dest2)
                                    stats['copied'] += 1
                            except Exception as e:
                                stats['errors'].append(f"エラー: {file2['path']} -> {dest2}: {e}")
                        else:
                            stats['copied'] += 1
                else:
                    # 異なる拡張子（HEIC vs JPGなど）
                    # HEICを優先
                    heic_file = file1 if ext1 == '.HEIC' else file2
                    jpg_file = file2 if ext1 == '.HEIC' else file1
                    
                    dest_file = output_date_folder / heic_file['filename']
                    
                    if not dry_run:
                        try:
                            if not dest_file.exists():
                                shutil.copy2(heic_file['path'], dest_file)
                                stats['copied'] += 1
                            else:
                                stats['skipped_jpg_when_heic_exists'] += 1
                        except Exception as e:
                            stats['errors'].append(f"エラー: {heic_file['path']} -> {dest_file}: {e}")
                    else:
                        stats['copied'] += 1
                        stats['skipped_jpg_when_heic_exists'] += 1
                        
            elif file1:
                # folder1にのみ存在
                dest_file = output_date_folder / file1['filename']
                if not dry_run:
                    try:
                        if not dest_file.exists():
                            shutil.copy2(file1['path'], dest_file)
                            stats['copied'] += 1
                    except Exception as e:
                        stats['errors'].append(f"エラー: {file1['path']} -> {dest_file}: {e}")
                else:
                    stats['copied'] += 1
                    
            elif file2:
                # folder2にのみ存在
                dest_file = output_date_folder / file2['filename']
                if not dry_run:
                    try:
                        if not dest_file.exists():
                            shutil.copy2(file2['path'], dest_file)
                            stats['copied'] += 1
                    except Exception as e:
                        stats['errors'].append(f"エラー: {file2['path']} -> {dest_file}: {e}")
                else:
                    stats['copied'] += 1
    
    # 年フォルダも処理（FOLDER2にある場合）
    print()
    print("年フォルダを処理中...")
    for year_folder in FOLDER2.iterdir():
        if year_folder.is_dir() and year_folder.name.isdigit() and len(year_folder.name) == 4:
            # 年フォルダ（例: 2023, 2024, 2025）
            output_year_folder = OUTPUT_FOLDER / year_folder.name
            if not dry_run:
                output_year_folder.mkdir(exist_ok=True)
            
            for file_path in year_folder.iterdir():
                if file_path.is_file():
                    dest_file = output_year_folder / file_path.name
                    if not dry_run:
                        try:
                            if not dest_file.exists():
                                shutil.copy2(file_path, dest_file)
                                stats['copied'] += 1
                        except Exception as e:
                            stats['errors'].append(f"エラー: {file_path} -> {dest_file}: {e}")
                    else:
                        stats['copied'] += 1
    
    # その他のフォルダも処理（create_date_not_foundなど）
    print()
    print("その他のフォルダを処理中...")
    special_folders = ['create_date_not_found', 'iPhone_Michino_tmp']
    for folder_name in special_folders:
        special_folder = FOLDER2 / folder_name
        if special_folder.exists() and special_folder.is_dir():
            output_special_folder = OUTPUT_FOLDER / folder_name
            if not dry_run:
                output_special_folder.mkdir(exist_ok=True)
            
            for file_path in special_folder.iterdir():
                if file_path.is_file():
                    dest_file = output_special_folder / file_path.name
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
    print("【マージ結果】")
    print(f"  コピー予定/コピーしたファイル数: {stats['copied']}")
    print(f"  完全に同一ファイル（スキップ）: {stats['skipped_exact_duplicate']}")
    print(f"  JPG（HEICが存在するためスキップ）: {stats['skipped_jpg_when_heic_exists']}")
    if stats['errors']:
        print(f"  エラー数: {len(stats['errors'])}")
        for error in stats['errors'][:10]:  # 最初の10件のみ表示
            print(f"    {error}")
        if len(stats['errors']) > 10:
            print(f"    ... 他 {len(stats['errors']) - 10} 件のエラー")
    print("=" * 80)
    
    if dry_run:
        print()
        print("これはDRY RUNです。実際にはコピーしていません。")
        print("実際にマージするには: python merge_photos_generic.py --execute <folder1> <folder2> <output>")
    
    return stats

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("使用方法: python merge_photos_generic.py [--execute] <folder1> <folder2> <output_folder>")
        print("例: python merge_photos_generic.py iPhone_12_Michino iPhone_Michino iPhone_Michino_Merged")
        sys.exit(1)
    
    dry_run = '--execute' not in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != '--execute']
    
    folder1 = args[0]
    folder2 = args[1]
    output = args[2]
    
    if dry_run:
        print("DRY RUNモードで実行します（実際にはコピーしません）")
        print("実際にマージするには: python merge_photos_generic.py --execute <folder1> <folder2> <output>")
        print()
    
    merge_photos(folder1, folder2, output, dry_run=dry_run)

