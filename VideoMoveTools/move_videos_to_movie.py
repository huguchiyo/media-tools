#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
動画ファイルを日付フォルダからmovieフォルダに移動し、リネームするスクリプト

cameraフォルダから動画をmovieフォルダに移動します。
移動時に、ファイル名に日付プレフィックスを追加します（例：2025_0102_IMG_0363.MOV）

使用方法:
    python move_videos_to_movie.py [--source SOURCE_DIR] [--dry-run]
"""

import os
import sys
import shutil
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Windowsでの文字化け対策
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# IDE/パイプから実行時もすぐ表示されるようにバッファを無効化
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# 動画ファイルの拡張子
VIDEO_EXTENSIONS = {'.mp4', '.MP4', '.mov', '.MOV', '.m2ts', '.M2TS', '.mts', '.MTS', '.avi', '.AVI', '.mkv', '.MKV'}

# デフォルトのソースフォルダ
DEFAULT_SOURCE_DIRS = [
    'G:/Users/chiyo/Pictures/camera'
]

# デフォルトの移動先フォルダ
DEFAULT_TARGET_DIR = 'G:/Users/chiyo/Pictures/movie'


def extract_date_from_folder(folder_name: str) -> Optional[tuple]:
    """
    フォルダ名から日付を抽出
    
    Args:
        folder_name: フォルダ名（例：2024-01-15 または 2024）
        
    Returns:
        (year, month_day) タプル、失敗時はNone
        month_dayがNoneの場合は年フォルダ（例：2024）
    """
    # 日付フォルダ（例：2024-01-15）
    match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', folder_name)
    if match:
        year = match.group(1)
        month = match.group(2)
        day = match.group(3)
        return year, f"{month}{day}"
    
    # 年フォルダ（例：2024）
    match = re.match(r'^(\d{4})$', folder_name)
    if match:
        year = match.group(1)
        return year, None  # month_dayがNoneの場合は年フォルダ
    
    return None


def extract_date_from_filename(filename: str) -> Optional[tuple]:
    """
    ファイル名から日付を抽出（既にリネーム済みの場合）
    
    Args:
        filename: ファイル名（例：2022_0701_IMG_4509.MOV）
        
    Returns:
        (year, month_day, original_name) タプル、失敗時はNone
    """
    # パターン: 2022_0701_IMG_4509.MOV
    match = re.match(r'^(\d{4})_(\d{4})_(.+)$', filename)
    if match:
        year = match.group(1)
        month_day = match.group(2)
        original_name = match.group(3)
        return year, month_day, original_name
    
    return None


def generate_new_filename(original_filename: str, year: str, month_day: str) -> str:
    """
    新しいファイル名を生成
    
    Args:
        original_filename: 元のファイル名
        year: 年（例：2025）
        month_day: 月日（例：0102）
        
    Returns:
        新しいファイル名（例：2025_0102_IMG_0363.MOV）
    """
    return f"{year}_{month_day}_{original_filename}"


def move_videos_from_source(
    source_dir: Path,
    target_base_dir: Path,
    dry_run: bool = True
) -> Dict[str, any]:
    """
    ソースフォルダから動画を移動
    
    Args:
        source_dir: ソースフォルダ（例：camera）
        target_base_dir: 移動先のベースフォルダ（例：movie）
        dry_run: Trueの場合は実際には移動しない
        
    Returns:
        統計情報の辞書（moved_filesリストを含む）
    """
    stats = {
        'processed': 0,
        'moved': 0,
        'skipped_duplicate': 0,
        'skipped_no_date': 0,
        'errors': [],
        'moved_files': []  # 移動したファイルのリスト
    }
    
    files_to_move = []
    folders_to_check_empty = set()  # 空になったフォルダを記録

    print("  ソースフォルダをスキャンしています...", flush=True)
    # 日付フォルダと年フォルダをスキャン
    for root, dirs, files in os.walk(source_dir):
        folder_name = os.path.basename(root)
        folder_path = Path(root)
        
        # フォルダタイプを判定
        date_info = extract_date_from_folder(folder_name)
        if not date_info:
            continue
        
        year, month_day = date_info
        
        for file in files:
            file_path = folder_path / file
            ext = file_path.suffix
            
            if ext not in VIDEO_EXTENSIONS:
                continue
            
            # ファイル名が既にリネーム済みかチェック
            filename_date_info = extract_date_from_filename(file)
            
            if filename_date_info:
                # 既にリネーム済み（例：2022_0701_IMG_4509.MOV）
                # 年フォルダ内の動画は全てリネーム済み
                file_year, file_month_day, original_name = filename_date_info
                new_filename = file  # リネーム不要
                target_year_dir = target_base_dir / file_year
                new_file_path = target_year_dir / new_filename
                
                files_to_move.append({
                    'source': file_path,
                    'dest': new_file_path,
                    'year': file_year,
                    'month_day': file_month_day,  # 追加
                    'original_name': original_name,
                    'new_name': new_filename,
                    'source_folder': folder_path
                })
            else:
                # リネームされていない動画（日付フォルダ内のみ）
                # 年フォルダ内の動画は全てリネーム済みのため、ここに来るのは日付フォルダ内の動画のみ
                if month_day is None:
                    # 念のため：年フォルダ内でリネームされていない動画（通常は発生しない）
                    print(f"  警告: 年フォルダ内のリネームされていない動画をスキップ: {file_path.relative_to(source_dir)}")
                    stats['skipped_no_date'] += 1
                    continue
                
                # 日付フォルダ内のリネームされていない動画
                new_filename = generate_new_filename(file, year, month_day)
                target_year_dir = target_base_dir / year
                new_file_path = target_year_dir / new_filename
                
                files_to_move.append({
                    'source': file_path,
                    'dest': new_file_path,
                    'year': year,
                    'month_day': month_day,  # 追加
                    'original_name': file,
                    'new_name': new_filename,
                    'source_folder': folder_path
                })
    
    total = len(files_to_move)
    print(f"  処理対象: {total}個の動画ファイル", flush=True)
    
    # 処理を実行
    for i, item in enumerate(files_to_move, 1):
        source = item['source']
        dest = item['dest']
        year = item['year']
        month_day = item['month_day']  # 追加
        original_name = item['original_name']
        new_name = item['new_name']
        progress = f"[{i}/{total}]"
        print(f"  {progress} 件目: {source.name} ...", flush=True)
        
        stats['processed'] += 1
        
        # 年フォルダが存在しない場合は作成
        year_folder = dest.parent
        if not year_folder.exists():
            if not dry_run:
                year_folder.mkdir(parents=True, exist_ok=True)
            print(f"  {progress} [新規作成] 年フォルダ: {year}/", flush=True)
        
        # 重複判定: 移動先に同じファイル名が既にあるか（ファイル名のみで判定）
        if dest.exists():
            print(f"  {progress} [既に存在するため削除] 移動元: {source.relative_to(source_dir)}", flush=True)
            print(f"                        移動先（既存）: {dest.relative_to(target_base_dir)}")
            print(f"                        （同一ファイル名のため重複と判定）")
            if not dry_run:
                try:
                    source.unlink()
                    print(f"  {progress} [削除完了] 元のファイルを削除しました", flush=True)
                    stats['skipped_duplicate'] += 1
                except Exception as e:
                    error_msg = f"削除エラー: {source.relative_to(source_dir)} -> {str(e)}"
                    print(f"  {progress} [エラー] {error_msg}", flush=True)
                    stats['errors'].append(error_msg)
            else:
                print(f"  {progress} [削除予定] 元のファイルを削除します", flush=True)
                stats['skipped_duplicate'] += 1
            continue
        
        # 移動を実行
        try:
            if dry_run:
                print(f"  {progress} [移動予定] {source.relative_to(source_dir)}", flush=True)
                print(f"            -> {dest.relative_to(target_base_dir)}")
            else:
                # 年フォルダが存在しない場合は作成
                year_folder.mkdir(parents=True, exist_ok=True)
                try:
                    size_mb = source.stat().st_size / (1024 * 1024)
                    size_str = f" ({size_mb:.1f} MB)"
                except Exception:
                    size_str = ""
                print(f"  {progress} [移動中] {source.relative_to(source_dir)} -> ...{size_str}", flush=True)
                # 同一ドライブなら os.rename（一瞬）、別ドライブなら shutil.move（コピー＋削除）
                src_resolved = source.resolve()
                dest_resolved = dest.resolve()
                same_drive = (
                    getattr(src_resolved, 'drive', '') and getattr(dest_resolved, 'drive', '')
                    and src_resolved.drive.upper() == dest_resolved.drive.upper()
                )
                if same_drive:
                    os.rename(str(src_resolved), str(dest))
                else:
                    shutil.move(str(src_resolved), str(dest))
                print(f"  {progress} [移動完了] {source.relative_to(source_dir)}", flush=True)
                print(f"            -> {dest.relative_to(target_base_dir)}")
            
            stats['moved'] += 1
            stats['moved_files'].append({
                'source': str(source.relative_to(source_dir)),
                'dest': str(dest.relative_to(target_base_dir)),
                'year': year,
                'original_name': original_name,
                'new_name': new_name
            })
            
            # 移動元フォルダを記録（空になったら削除するため）
            if 'source_folder' in item:
                folders_to_check_empty.add(item['source_folder'])
            
        except Exception as e:
            error_msg = f"エラー: {source.relative_to(source_dir)} -> {str(e)}"
            print(f"  {progress} [エラー] {error_msg}", flush=True)
            stats['errors'].append(error_msg)
    
    # 空になったフォルダを削除
    if not dry_run:
        for folder_path in folders_to_check_empty:
            try:
                # フォルダ内にファイルが残っているかチェック
                remaining_files = [f for f in folder_path.iterdir() if f.is_file()]
                if not remaining_files:
                    # サブフォルダもチェック
                    remaining_dirs = [d for d in folder_path.iterdir() if d.is_dir()]
                    if not remaining_dirs:
                        folder_path.rmdir()
                        print(f"  [削除] 空になったフォルダを削除: {folder_path.relative_to(source_dir)}")
            except Exception as e:
                print(f"  [警告] フォルダ削除エラー: {folder_path.relative_to(source_dir)} -> {e}")
    
    return stats


def _write_moved_log_md(md_path: Path, logs: list) -> None:
    """移動ログを人が確認しやすい Markdown で書き出す。"""
    lines = [
        "# 動画移動ログ（人が確認用）",
        "",
        "JSON は `moved_videos_log.json` を参照。",
        "",
    ]
    for i, run in enumerate(reversed(logs)):  # 新しい実行が上に来る
        date = run.get('date', '')[:19].replace('T', ' ')
        target = run.get('target_dir', '')
        sources = run.get('source_dirs', [])
        count = run.get('moved_count', 0)
        files = run.get('moved_files', [])
        lines.append(f"## 実行 {len(logs) - i} — {date}")
        lines.append("")
        lines.append(f"- **移動先**: `{target}`")
        lines.append(f"- **ソース**: {', '.join(sources)}")
        lines.append(f"- **移動数**: {count} 件")
        lines.append("")
        if files:
            lines.append("| 移動元 | 移動先（年/ファイル名） | 年 |")
            lines.append("|--------|------------------------|-----|")
            for f in files:
                src = f.get('source', '').replace('|', '\\|')
                dest = f.get('dest', '').replace('|', '\\|')
                year = f.get('year', '')
                lines.append(f"| {src} | {dest} | {year} |")
            lines.append("")
        lines.append("---")
        lines.append("")
    try:
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"確認用ログを保存しました: {md_path}")
    except Exception as e:
        print(f"警告: 確認用ログの保存に失敗しました: {e}")


def move_videos_to_movie(
    source_dirs: List[str],
    target_dir: str,
    dry_run: bool = True
) -> None:
    """
    複数のソースフォルダから動画をmovieフォルダに移動
    
    Args:
        source_dirs: ソースフォルダのリスト
        target_dir: 移動先フォルダ
        dry_run: Trueの場合は実際には移動しない
    """
    target_path = Path(target_dir)
    
    print("=" * 60, flush=True)
    print("動画ファイル移動スクリプト", flush=True)
    print("=" * 60, flush=True)
    print(f"モード: {'DRY RUN（実際には移動しません）' if dry_run else '実行モード（実際に移動します）'}", flush=True)
    print(f"移動先: {target_dir}", flush=True)
    print(flush=True)
    
    total_stats = {
        'processed': 0,
        'moved': 0,
        'skipped_duplicate': 0,
        'skipped_no_date': 0,
        'errors': [],
        'moved_files': []
    }
    
    for source_dir in source_dirs:
        source_path = Path(source_dir)
        
        if not source_path.exists():
            print(f"警告: ソースフォルダが見つかりません: {source_dir}")
            continue
        
        print(f"処理中: {source_dir}", flush=True)
        stats = move_videos_from_source(source_path, target_path, dry_run)
        
        # 統計情報を集計
        for key in total_stats:
            if key == 'errors':
                total_stats[key].extend(stats[key])
            elif key == 'moved_files':
                total_stats[key].extend(stats[key])
            else:
                total_stats[key] += stats[key]
        
        print()
    
    # 統計情報を表示
    print("=" * 60)
    print("処理結果")
    print("=" * 60)
    print(f"処理対象: {total_stats['processed']}個")
    print(f"移動: {total_stats['moved']}個")
    print(f"スキップ（重複）: {total_stats['skipped_duplicate']}個")
    print(f"エラー: {len(total_stats['errors'])}個")
    
    # 移動したファイルのリストを保存
    if not dry_run and total_stats['moved_files']:
        import json
        from datetime import datetime
        
        # ログファイルはスクリプトと同じフォルダに保存
        script_dir = Path(__file__).parent
        log_file = script_dir / 'moved_videos_log.json'
        log_data = {
            'date': datetime.now().isoformat(),
            'target_dir': target_dir,
            'source_dirs': source_dirs,
            'moved_count': len(total_stats['moved_files']),
            'moved_files': total_stats['moved_files']
        }
        
        # 既存のログを読み込み（配列に追加）
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
                    if not isinstance(existing_logs, list):
                        existing_logs = [existing_logs]
            except:
                existing_logs = []
        else:
            existing_logs = []
        
        existing_logs.append(log_data)
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)
            print(f"\n移動したファイルのリストを保存しました: {log_file}")
            # 人が確認しやすい Markdown も出力
            _write_moved_log_md(script_dir / 'moved_videos_log.md', existing_logs)
            # 移動結果を表示
            print("\n【今回の移動結果】")
            by_year = {}
            for f in total_stats['moved_files']:
                y = f.get('year', '')
                if y not in by_year:
                    by_year[y] = []
                by_year[y].append(f)
            for year in sorted(by_year.keys()):
                files = by_year[year]
                print(f"  {year}: {len(files)}本")
                for f in files:
                    print(f"    - {f.get('source', '')} → {f.get('dest', '')}")
        except Exception as e:
            print(f"\n警告: 移動リストの保存に失敗しました: {e}")
    
    if total_stats['errors']:
        print("\nエラー詳細:")
        for error in total_stats['errors'][:10]:  # 最初の10件のみ表示
            print(f"  - {error}")
        if len(total_stats['errors']) > 10:
            print(f"  ... 他 {len(total_stats['errors']) - 10}件")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Move videos from source folders to movie folder')
    parser.add_argument('--source', action='append', help='Source directory (can be specified multiple times)')
    parser.add_argument('--target', default=DEFAULT_TARGET_DIR, help='Target directory (default: movie)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no actual move)')
    parser.add_argument('--execute', action='store_true', help='Execute mode (actually move files)')
    parser.add_argument('--execute-yes', action='store_true', help='Execute mode without confirmation prompt')
    
    args = parser.parse_args()
    
    source_dirs = args.source if args.source else DEFAULT_SOURCE_DIRS
    
    if args.execute_yes:
        dry_run = False
    elif args.execute:
        print("警告: 実際にファイルを移動します。")
        try:
            response = input("続行しますか？ (yes/no): ")
            if response.lower() != 'yes':
                print("キャンセルしました。")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print("\nキャンセルしました。")
            sys.exit(0)
        dry_run = False
    else:
        dry_run = True
    
    move_videos_to_movie(source_dirs, args.target, dry_run=dry_run)

