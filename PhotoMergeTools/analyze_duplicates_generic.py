#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iPhone写真フォルダの重複分析スクリプト（汎用版）
任意の2つのフォルダの重複を分析します
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def get_file_info(folder_path):
    """フォルダ内の全ファイル情報を取得"""
    files_info = defaultdict(list)
    
    if not folder_path.exists():
        print(f"警告: {folder_path} が見つかりません")
        return files_info
    
    for date_folder in folder_path.iterdir():
        if not date_folder.is_dir():
            continue
        
        date_str = date_folder.name
        
        for file_path in date_folder.iterdir():
            if file_path.is_file():
                filename = file_path.name
                file_stem = file_path.stem
                file_ext = file_path.suffix.upper()
                file_size = file_path.stat().st_size
                
                files_info[date_str].append({
                    'stem': file_stem,
                    'filename': filename,
                    'path': file_path,
                    'size': file_size,
                    'ext': file_ext
                })
    
    return files_info

def analyze_duplicates(folder1_name, folder2_name, output_report):
    """重複を分析してレポートを生成"""
    FOLDER1 = Path(folder1_name)
    FOLDER2 = Path(folder2_name)
    
    print("ファイル情報を収集中...")
    files1 = get_file_info(FOLDER1)
    files2 = get_file_info(FOLDER2)
    
    # 全ファイルを統合（日付フォルダごと）
    all_dates = set(files1.keys()) | set(files2.keys())
    
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("iPhone写真フォルダ 重複分析レポート")
    report_lines.append(f"フォルダ1: {FOLDER1}")
    report_lines.append(f"フォルダ2: {FOLDER2}")
    report_lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # 統計情報
    total_files1 = sum(len(files) for files in files1.values())
    total_files2 = sum(len(files) for files in files2.values())
    
    report_lines.append("【フォルダ統計】")
    report_lines.append(f"  {FOLDER1}: {total_files1} ファイル")
    report_lines.append(f"  {FOLDER2}: {total_files2} ファイル")
    report_lines.append(f"  日付フォルダ数: {len(all_dates)}")
    report_lines.append("")
    
    # 重複分析
    duplicates_by_date = {}
    heic_vs_jpg = []
    exact_duplicates = []
    unique_in_folder1 = []
    unique_in_folder2 = []
    
    for date_str in sorted(all_dates):
        files_in_date1 = {f['stem']: f for f in files1.get(date_str, [])}
        files_in_date2 = {f['stem']: f for f in files2.get(date_str, [])}
        
        all_stems = set(files_in_date1.keys()) | set(files_in_date2.keys())
        
        date_duplicates = []
        
        for stem in all_stems:
            file1 = files_in_date1.get(stem)
            file2 = files_in_date2.get(stem)
            
            if file1 and file2:
                # 両方に存在
                ext1 = file1['ext']
                ext2 = file2['ext']
                
                if ext1 == ext2:
                    # 同じ拡張子
                    if file1['size'] == file2['size']:
                        # サイズも同じ（完全に同一の可能性が高い）
                        exact_duplicates.append({
                            'date': date_str,
                            'stem': stem,
                            'ext': ext1,
                            'file1': file1,
                            'file2': file2
                        })
                    else:
                        # サイズが異なる（異なるファイル）
                        date_duplicates.append({
                            'type': 'same_name_diff_size',
                            'date': date_str,
                            'stem': stem,
                            'ext': ext1,
                            'file1': file1,
                            'file2': file2
                        })
                else:
                    # 異なる拡張子（HEIC vs JPGなど）
                    heic_vs_jpg.append({
                        'date': date_str,
                        'stem': stem,
                        'file1': file1,
                        'file2': file2
                    })
                    date_duplicates.append({
                        'type': 'different_ext',
                        'date': date_str,
                        'stem': stem,
                        'file1': file1,
                        'file2': file2
                    })
            elif file1:
                # folder1にのみ存在
                unique_in_folder1.append({
                    'date': date_str,
                    'file': file1
                })
            elif file2:
                # folder2にのみ存在
                unique_in_folder2.append({
                    'date': date_str,
                    'file': file2
                })
        
        if date_duplicates:
            duplicates_by_date[date_str] = date_duplicates
    
    # レポート出力
    report_lines.append("【重複サマリー】")
    report_lines.append(f"  完全に同一ファイル（名前・拡張子・サイズ）: {len(exact_duplicates)} 件")
    report_lines.append(f"  HEIC vs JPG の重複: {len(heic_vs_jpg)} 件")
    report_lines.append(f"  {FOLDER1} にのみ存在: {len(unique_in_folder1)} ファイル")
    report_lines.append(f"  {FOLDER2} にのみ存在: {len(unique_in_folder2)} ファイル")
    report_lines.append("")
    
    # 詳細レポート
    if exact_duplicates:
        report_lines.append("【完全に同一ファイル（削除候補）】")
        report_lines.append("")
        for dup in exact_duplicates[:50]:  # 最初の50件のみ表示
            report_lines.append(f"  {dup['date']}/{dup['stem']}{dup['ext']}")
            report_lines.append(f"    {FOLDER1}: {dup['file1']['size']:,} bytes")
            report_lines.append(f"    {FOLDER2}: {dup['file2']['size']:,} bytes")
        if len(exact_duplicates) > 50:
            report_lines.append(f"  ... 他 {len(exact_duplicates) - 50} 件")
        report_lines.append("")
    
    if heic_vs_jpg:
        report_lines.append("【HEIC vs JPG 重複（HEIC優先で保持）】")
        report_lines.append("")
        for dup in heic_vs_jpg[:50]:  # 最初の50件のみ表示
            file1 = dup['file1']
            file2 = dup['file2']
            heic_file = file1 if file1['ext'] == '.HEIC' else file2
            jpg_file = file2 if file1['ext'] == '.HEIC' else file1
            
            report_lines.append(f"  {dup['date']}/{dup['stem']}")
            report_lines.append(f"    HEIC: {heic_file['path']} ({heic_file['size']:,} bytes)")
            report_lines.append(f"    JPG:  {jpg_file['path']} ({jpg_file['size']:,} bytes) → スキップ")
        if len(heic_vs_jpg) > 50:
            report_lines.append(f"  ... 他 {len(heic_vs_jpg) - 50} 件")
        report_lines.append("")
    
    # 日付フォルダごとの重複数
    if duplicates_by_date:
        report_lines.append("【日付フォルダごとの重複数】")
        report_lines.append("")
        for date_str in sorted(duplicates_by_date.keys()):
            count = len(duplicates_by_date[date_str])
            report_lines.append(f"  {date_str}: {count} 件の重複")
        report_lines.append("")
    
    # レポートをファイルに保存
    report_text = "\n".join(report_lines)
    with open(output_report, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(f"\nレポートを {output_report} に保存しました")
    print("\n" + report_text)
    
    return {
        'exact_duplicates': exact_duplicates,
        'heic_vs_jpg': heic_vs_jpg,
        'unique_in_folder1': unique_in_folder1,
        'unique_in_folder2': unique_in_folder2,
        'total_files1': total_files1,
        'total_files2': total_files2
    }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用方法: python analyze_duplicates_generic.py <folder1> <folder2> [output_report]")
        print("例: python analyze_duplicates_generic.py iPhone_12_Michino iPhone_Michino duplicate_report_michino.txt")
        sys.exit(1)
    
    folder1 = sys.argv[1]
    folder2 = sys.argv[2]
    output_report = sys.argv[3] if len(sys.argv) > 3 else "duplicate_report.txt"
    
    analyze_duplicates(folder1, folder2, output_report)

