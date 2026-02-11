#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
camera → movie 移動 → 移動記録 → YouTubeアップロード → アップロード結果記録 を一括または段階実行するワークフロー。

流れ:
  1. camera フォルダの動画をリネームして movie/YYYY/ に移動（VideoMoveTools）
  2. どのフォルダにどの動画が移動したかを記録し、結果を表示（同上）
  3. movie 内の動画のうち uploaded_from_youtube.txt に無いものを確認し結果を表示。該当年を YouTube にアップロード（youtube）
  4. アップロード結果を youtube/data/upload_runs.json に記録（youtube_upload.py が記録）

使い方:
  # ドライラン（移動もアップロードも実行しない）
  python workflow.py --move --upload-from-move-log --dry-run

  # 移動のみ実行（確認プロンプトなし）
  python workflow.py --move

  # movie 内の未アップロード動画を表示し、該当年をアップロード（確認後に本番）
  python workflow.py --upload-from-move-log

  # 確認プロンプトをスキップしてアップロード（非対話用）
  python workflow.py --upload-from-move-log --yes

  # 移動 → アップロードを続けて実行
  python workflow.py --move --upload-from-move-log
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# このスクリプトの場所 = Tools/
TOOLS_DIR = Path(__file__).resolve().parent
VIDEO_MOVE_TOOLS_DIR = TOOLS_DIR / "VideoMoveTools"
YOUTUBE_DIR = TOOLS_DIR / "youtube"
MOVED_LOG_PATH = VIDEO_MOVE_TOOLS_DIR / "moved_videos_log.json"
UPLOADED_TITLES_PATH = YOUTUBE_DIR / "data" / "uploaded_from_youtube.txt"
DEFAULT_MOVIE_DIR = "G:/Users/chiyo/Pictures/movie"

# youtube_upload と同じ動画拡張子
VIDEO_EXTENSIONS = {".mp4", ".MP4", ".mov", ".MOV", ".m2ts", ".M2TS", ".mts", ".MTS", ".avi", ".AVI", ".mkv", ".MKV", ".wmv", ".flv", ".webm"}


def get_target_dir_from_move_log() -> Optional[str]:
    """直近の移動ログから移動先ベースパスを取得。無ければ None。"""
    if not MOVED_LOG_PATH.exists():
        return None
    try:
        with open(MOVED_LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    if not data:
        return None
    latest = data[-1] if isinstance(data, list) else data
    return latest.get("target_dir")


def get_unuploaded_by_year(
    movie_dir: str, uploaded_titles_path: Path
) -> Tuple[dict, str]:
    """
    movie フォルダをスキャンし、uploaded_from_youtube.txt に無い動画を年ごとに返す。

    Returns:
        (by_year, movie_dir): by_year は { year: [ (full_title, filename), ... ] }、movie_dir はそのまま。
    """
    movie_path = Path(movie_dir)
    if not movie_path.is_dir():
        return {}, movie_dir

    uploaded = set()
    if uploaded_titles_path.exists():
        with open(uploaded_titles_path, "r", encoding="utf-8") as f:
            for line in f:
                t = line.strip()
                if t:
                    uploaded.add(t)

    by_year = {}
    for sub in sorted(movie_path.iterdir()):
        if not sub.is_dir():
            continue
        year = sub.name
        if len(year) != 4 or not year.isdigit():
            continue
        for fpath in sub.iterdir():
            if not fpath.is_file():
                continue
            if fpath.suffix not in VIDEO_EXTENSIONS:
                continue
            name = fpath.name
            base = name.rsplit(".", 1)[0] if "." in name else name
            # youtube_upload と同じ: タイトル = ファイル名（拡張子除く、_ をスペースに）。年は付けない。
            full_title = base.replace("_", " ")
            if full_title in uploaded:
                continue
            if year not in by_year:
                by_year[year] = []
            by_year[year].append((full_title, name))

    return by_year, movie_dir


def run_move(dry_run: bool) -> bool:
    """VideoMoveTools の移動スクリプトを実行する。成功で True。"""
    cmd = [sys.executable, str(VIDEO_MOVE_TOOLS_DIR / "move_videos_to_movie.py")]
    if dry_run:
        cmd.append("--dry-run")
    else:
        cmd.append("--execute-yes")
    try:
        subprocess.run(cmd, cwd=str(VIDEO_MOVE_TOOLS_DIR), check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Move script failed: {e}", file=sys.stderr)
        return False


def run_upload_for_year(
    target_dir: str, year: str, dry_run: bool, no_fetch_list: bool, first_year: bool
) -> bool:
    """指定年の movie/YYYY を YouTube にアップロードする。成功で True。"""
    import os
    dir_path = os.path.join(target_dir, year).replace("\\", "/")
    cmd = [sys.executable, str(YOUTUBE_DIR / "youtube_upload.py"), "--dir", dir_path]
    if dry_run:
        cmd.append("--dry-run")
    if no_fetch_list or (not first_year):
        cmd.append("--no-fetch-list")
    try:
        subprocess.run(cmd, cwd=str(YOUTUBE_DIR), check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Upload failed for {year}: {e}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Workflow: move videos from camera to movie, then upload moved years to YouTube."
    )
    parser.add_argument("--move", action="store_true", help="Run move step (camera → movie)")
    parser.add_argument("--upload-from-move-log", action="store_true", help="Upload years that had moves in latest move log")
    parser.add_argument("--years", nargs="*", metavar="YEAR", help="Override years to upload (e.g. 2024 2025); ignores move log for upload list")
    parser.add_argument("--dry-run", action="store_true", help="Do not actually move or upload")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip upload confirmation prompt; upload immediately")
    parser.add_argument("--no-fetch-list", action="store_true", help="Do not fetch uploaded list from YouTube API (use local file only)")
    parser.add_argument("--movie-dir", default=DEFAULT_MOVIE_DIR, help=f"Movie folder to scan for unuploaded videos (default: {DEFAULT_MOVIE_DIR})")
    args = parser.parse_args()

    if not args.move and not args.upload_from_move_log and not args.years:
        parser.print_help()
        print("\nExample: python workflow.py --move --upload-from-move-log --dry-run", file=sys.stderr)
        sys.exit(0)

    if args.move:
        print("=== Step 1: Move videos (camera → movie) ===")
        if not run_move(args.dry_run):
            sys.exit(1)
        print()

    if args.upload_from_move_log or args.years is not None:
        if args.years:
            years = sorted(set(args.years))
            target_dir = get_target_dir_from_move_log() or args.movie_dir
            print(f"Upload years (from --years): {years}")
            print(f"Target base: {target_dir}")
        else:
            # movie をスキャンし、uploaded_from_youtube.txt に無い動画を年ごとに表示
            by_year, target_dir = get_unuploaded_by_year(args.movie_dir, UPLOADED_TITLES_PATH)
            print(f"Movie folder: {target_dir}")
            print(f"Uploaded list: {UPLOADED_TITLES_PATH} ({'exists' if UPLOADED_TITLES_PATH.exists() else 'not found'})")
            print()
            print("【未アップロード動画】")
            if not by_year:
                print("  未アップロードの動画はありません。")
                sys.exit(0)
            total = 0
            for year in sorted(by_year.keys()):
                items = by_year[year]
                total += len(items)
                print(f"  {year}: {len(items)}本")
                for title, _ in items:
                    print(f"    - {title}")
            print(f"  合計: {total}本")
            print()
            years = sorted(by_year.keys())
            print(f"アップロード対象の年: {years}")
            print(f"Target base: {target_dir}")

        # 本番アップロード時は、先にドライランで対象を表示してから確認
        do_upload = args.dry_run
        if not args.dry_run:
            print("=== Step 2a: アップロード対象の確認（ドライラン） ===")
            for i, year in enumerate(years):
                first = i == 0
                print(f"Preview year: {year}")
                if not run_upload_for_year(target_dir, year, dry_run=True, no_fetch_list=args.no_fetch_list, first_year=first):
                    sys.exit(1)
            print()
            if args.yes:
                do_upload = True
            else:
                try:
                    reply = input("上記を YouTube にアップロードしますか？ (yes/no): ").strip().lower()
                    do_upload = reply in ("yes", "y")
                except (EOFError, KeyboardInterrupt):
                    print("\nキャンセルしました。")
                    sys.exit(0)
            if not do_upload:
                print("アップロードをスキップしました。")
                sys.exit(0)
            print()

        print("=== Step 2: Upload to YouTube ===")
        for i, year in enumerate(years):
            first = i == 0
            print(f"Uploading year: {year} (fetch_list={not args.no_fetch_list and first})")
            if not run_upload_for_year(target_dir, year, args.dry_run, args.no_fetch_list, first):
                sys.exit(1)
        print("Upload step finished. Results recorded in youtube/data/upload_runs.json")


if __name__ == "__main__":
    main()
