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
import subprocess
from pathlib import Path
from datetime import datetime
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

DATE_SOURCE_LABELS = {
    'folder_name': '日付フォルダ',
    'filename_renamed': '既存ファイル名',
    'filename': 'ファイル名',
    'metadata': 'メタデータ',
    'mtime': '更新日時',
    'unknown': 'unknown',
}


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


def _normalize_date_parts(year: str, month: str, day: str) -> Optional[Tuple[str, str]]:
    """年・月・日を検証し、(year, MMDD) を返す。"""
    try:
        dt = datetime(int(year), int(month), int(day))
    except ValueError:
        return None
    return f"{dt.year:04d}", f"{dt.month:02d}{dt.day:02d}"


def infer_date_from_filename_patterns(filename: str) -> Optional[Tuple[str, str]]:
    """
    ファイル名から日付を推定する。

    例:
      - 20250423_123456.MOV
      - IMG_2025-04-23_101010.MOV
      - 2025_0423_trip.mov
    """
    stem = Path(filename).stem
    patterns = [
        r'(?<!\d)((?:19|20)\d{2})(\d{2})(\d{2})(?!\d)',
        r'(?<!\d)((?:19|20)\d{2})[-_.](\d{2})[-_.](\d{2})(?!\d)',
        r'(?<!\d)((?:19|20)\d{2})[-_.](\d{2})(\d{2})(?!\d)',
    ]
    for pattern in patterns:
        match = re.search(pattern, stem)
        if not match:
            continue
        normalized = _normalize_date_parts(match.group(1), match.group(2), match.group(3))
        if normalized:
            return normalized
    return None


def _parse_metadata_datetime(value: str) -> Optional[Tuple[str, str]]:
    """ffprobe などで得た日時文字列を (year, MMDD) に変換する。"""
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    text = text.replace('/', '-')
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'

    # ISO形式や "2025-04-23 10:20:30" を優先
    try:
        dt = datetime.fromisoformat(text)
        return f"{dt.year:04d}", f"{dt.month:02d}{dt.day:02d}"
    except ValueError:
        pass

    # "2025:04:23 10:20:30" のような形式
    match = re.search(r'((?:19|20)\d{2})[:\-](\d{2})[:\-](\d{2})', text)
    if not match:
        return None
    return _normalize_date_parts(match.group(1), match.group(2), match.group(3))


def extract_date_from_metadata(file_path: Path) -> Optional[Tuple[str, str]]:
    """動画メタデータから日付を推定する。ffprobe が無ければ None。"""
    ffprobe_path = shutil.which('ffprobe')
    if not ffprobe_path:
        return None

    cmd = [
        ffprobe_path,
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_entries',
        'format_tags=creation_time,com.apple.quicktime.creationdate,date:'
        'stream_tags=creation_time,com.apple.quicktime.creationdate,date',
        str(file_path),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=10,
            check=False,
        )
    except Exception:
        return None

    if result.returncode != 0 or not result.stdout.strip():
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    tag_sets = []
    format_tags = ((payload.get('format') or {}).get('tags') or {})
    if format_tags:
        tag_sets.append(format_tags)
    for stream in payload.get('streams', []):
        tags = (stream or {}).get('tags') or {}
        if tags:
            tag_sets.append(tags)

    for tags in tag_sets:
        for key in ('creation_time', 'com.apple.quicktime.creationdate', 'date'):
            parsed = _parse_metadata_datetime(tags.get(key, ''))
            if parsed:
                return parsed
    return None


def extract_date_from_mtime(file_path: Path) -> Optional[Tuple[str, str]]:
    """更新日時から日付を推定する。"""
    try:
        dt = datetime.fromtimestamp(file_path.stat().st_mtime)
    except OSError:
        return None
    return f"{dt.year:04d}", f"{dt.month:02d}{dt.day:02d}"


def infer_date_for_direct_file(file_path: Path) -> Tuple[Optional[str], Optional[str], str, Optional[str], str]:
    """
    ソース直下ファイルの日付を推定する。

    Returns:
        (year, month_day, date_source, new_filename, note)
    """
    renamed = extract_date_from_filename(file_path.name)
    if renamed:
        year, month_day, _ = renamed
        return year, month_day, 'filename_renamed', file_path.name, '既に日付付きファイル名です'

    inferred_from_name = infer_date_from_filename_patterns(file_path.name)
    if inferred_from_name:
        year, month_day = inferred_from_name
        return year, month_day, 'filename', generate_new_filename(file_path.name, year, month_day), 'ファイル名から日付を推定しました'

    inferred_from_metadata = extract_date_from_metadata(file_path)
    if inferred_from_metadata:
        year, month_day = inferred_from_metadata
        return year, month_day, 'metadata', generate_new_filename(file_path.name, year, month_day), 'メタデータから撮影日を推定しました'

    inferred_from_mtime = extract_date_from_mtime(file_path)
    if inferred_from_mtime:
        year, month_day = inferred_from_mtime
        return year, month_day, 'mtime', generate_new_filename(file_path.name, year, month_day), '更新日時から日付を推定しました'

    return None, None, 'unknown', file_path.name, '日付を推定できないため unknown に移動します'


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


def _build_result_payload(source_dirs: List[str], target_dir: str, moved_files: List[Dict[str, str]], dry_run: bool) -> Dict[str, any]:
    rows = []
    mtime_count = 0
    unknown_count = 0
    for moved in moved_files:
        date_source = moved.get('date_source', '')
        if date_source == 'mtime':
            mtime_count += 1
        if date_source == 'unknown':
            unknown_count += 1
        rows.append({
            'from': moved.get('source', ''),
            'to': moved.get('dest', ''),
            'year': moved.get('year', ''),
            'date_source': date_source,
            'date_source_label': DATE_SOURCE_LABELS.get(date_source, date_source or '—'),
            'note': moved.get('note', ''),
        })
    return {
        'date': datetime.now().isoformat(),
        'source': source_dirs[0] if source_dirs else '',
        'source_dirs': source_dirs,
        'target': target_dir,
        'count': len(rows),
        'mtime_count': mtime_count,
        'unknown_count': unknown_count,
        'is_preview': dry_run,
        'rows': rows,
    }


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
        is_source_root = folder_path.resolve() == source_dir.resolve()
        
        # フォルダタイプを判定
        date_info = extract_date_from_folder(folder_name)
        if not date_info and not is_source_root:
            continue
        year = month_day = None
        if date_info:
            year, month_day = date_info
        
        for file in files:
            file_path = folder_path / file
            ext = file_path.suffix
            
            if ext not in VIDEO_EXTENSIONS:
                continue
            note = ''

            # ファイル名が既にリネーム済みかチェック
            filename_date_info = extract_date_from_filename(file)
            if filename_date_info:
                file_year, file_month_day, original_name = filename_date_info
                new_filename = file
                target_dir_name = file_year
                new_file_path = target_base_dir / target_dir_name / new_filename
                date_source = 'filename_renamed'
                year_value = file_year
                month_day_value = file_month_day
                note = '既に日付付きファイル名です'
            elif date_info:
                # リネームされていない動画（日付フォルダ内のみ）
                if month_day is None:
                    # 念のため：年フォルダ内でリネームされていない動画（通常は発生しない）
                    print(f"  警告: 年フォルダ内のリネームされていない動画をスキップ: {file_path.relative_to(source_dir)}")
                    stats['skipped_no_date'] += 1
                    continue
                new_filename = generate_new_filename(file, year, month_day)
                target_dir_name = year
                new_file_path = target_base_dir / target_dir_name / new_filename
                date_source = 'folder_name'
                year_value = year
                month_day_value = month_day
                note = '日付フォルダ名を使用しました'
            elif is_source_root:
                inferred_year, inferred_month_day, date_source, new_filename, note = infer_date_for_direct_file(file_path)
                if date_source == 'unknown':
                    target_dir_name = 'unknown'
                    new_file_path = target_base_dir / target_dir_name / new_filename
                    year_value = 'unknown'
                    month_day_value = None
                else:
                    target_dir_name = inferred_year
                    new_file_path = target_base_dir / target_dir_name / new_filename
                    year_value = inferred_year
                    month_day_value = inferred_month_day
            else:
                continue

            files_to_move.append({
                'source': file_path,
                'dest': new_file_path,
                'year': year_value,
                'month_day': month_day_value,
                'original_name': file,
                'new_name': new_filename,
                'source_folder': folder_path,
                'date_source': date_source,
                'note': note,
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
        date_source = item.get('date_source', '')
        date_source_label = DATE_SOURCE_LABELS.get(date_source, date_source or '—')
        note = item.get('note', '')
        progress = f"[{i}/{total}]"
        print(f"  {progress} 件目: {source.name} [{date_source_label}] ...", flush=True)
        
        stats['processed'] += 1
        
        # 移動先フォルダが存在しない場合は作成
        target_folder = dest.parent
        if not target_folder.exists():
            if not dry_run:
                target_folder.mkdir(parents=True, exist_ok=True)
            print(f"  {progress} [新規作成] 移動先フォルダ: {dest.parent.relative_to(target_base_dir)}", flush=True)
        if note:
            print(f"  {progress} [判定] {note}", flush=True)
        
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
                print(f"  {progress} [移動予定:{date_source_label}] {source.relative_to(source_dir)}", flush=True)
                print(f"            -> {dest.relative_to(target_base_dir)}")
            else:
                # 移動先フォルダが存在しない場合は作成
                target_folder.mkdir(parents=True, exist_ok=True)
                try:
                    size_mb = source.stat().st_size / (1024 * 1024)
                    size_str = f" ({size_mb:.1f} MB)"
                except Exception:
                    size_str = ""
                print(f"  {progress} [移動中:{date_source_label}] {source.relative_to(source_dir)} -> ...{size_str}", flush=True)
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
                print(f"  {progress} [移動完了:{date_source_label}] {source.relative_to(source_dir)}", flush=True)
                print(f"            -> {dest.relative_to(target_base_dir)}")
            
            stats['moved'] += 1
            stats['moved_files'].append({
                'source': str(source.relative_to(source_dir)),
                'dest': str(dest.relative_to(target_base_dir)),
                'year': year,
                'original_name': original_name,
                'new_name': new_name,
                'date_source': date_source,
                'note': note,
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
        mtime_count = run.get('mtime_count', 0)
        unknown_count = run.get('unknown_count', 0)
        files = run.get('moved_files', [])
        lines.append(f"## 実行 {len(logs) - i} — {date}")
        lines.append("")
        lines.append(f"- **移動先**: `{target}`")
        lines.append(f"- **ソース**: {', '.join(sources)}")
        lines.append(f"- **移動数**: {count} 件")
        lines.append(f"- **更新日時フォールバック**: {mtime_count} 件")
        lines.append(f"- **unknown 退避**: {unknown_count} 件")
        lines.append("")
        if files:
            lines.append("| 移動元 | 移動先（年/ファイル名） | 年 | 判定方法 |")
            lines.append("|--------|------------------------|-----|----------|")
            for f in files:
                src = f.get('source', '').replace('|', '\\|')
                dest = f.get('dest', '').replace('|', '\\|')
                year = f.get('year', '')
                date_source = f.get('date_source', '')
                label = DATE_SOURCE_LABELS.get(date_source, date_source or '—')
                lines.append(f"| {src} | {dest} | {year} | {label} |")
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
    mtime_count = sum(1 for f in total_stats['moved_files'] if f.get('date_source') == 'mtime')
    unknown_count = sum(1 for f in total_stats['moved_files'] if f.get('date_source') == 'unknown')
    print(f"更新日時フォールバック: {mtime_count}個")
    print(f"unknown 退避: {unknown_count}個")
    
    # 移動したファイルのリストを保存
    if not dry_run and total_stats['moved_files']:
        # ログファイルはスクリプトと同じフォルダに保存
        script_dir = Path(__file__).parent
        log_file = script_dir / 'moved_videos_log.json'
        log_data = {
            'date': datetime.now().isoformat(),
            'target_dir': target_dir,
            'source_dirs': source_dirs,
            'moved_count': len(total_stats['moved_files']),
            'mtime_count': mtime_count,
            'unknown_count': unknown_count,
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
                    label = DATE_SOURCE_LABELS.get(f.get('date_source', ''), f.get('date_source', ''))
                    print(f"    - [{label}] {f.get('source', '')} → {f.get('dest', '')}")
        except Exception as e:
            print(f"\n警告: 移動リストの保存に失敗しました: {e}")

    result_payload = _build_result_payload(source_dirs, target_dir, total_stats['moved_files'], dry_run=dry_run)
    if mtime_count:
        print("\n【確認が必要な候補】")
        print(f"  更新日時を使って日付推定した動画: {mtime_count}本")
        for row in result_payload['rows']:
            if row.get('date_source') == 'mtime':
                print(f"    - {row.get('from', '')} → {row.get('to', '')}")
    if unknown_count:
        print(f"  unknown に移動する動画: {unknown_count}本")
        for row in result_payload['rows']:
            if row.get('date_source') == 'unknown':
                print(f"    - {row.get('from', '')} → {row.get('to', '')}")

    print(f"__MOVE_RESULT__={json.dumps(result_payload, ensure_ascii=False)}", flush=True)
    
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

