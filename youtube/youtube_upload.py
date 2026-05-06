#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube動画アップロードスクリプト

このスクリプトは指定されたディレクトリ内の動画ファイルをYouTubeにアップロードします。
既にアップロード済みの動画はスキップされます。

使用方法:
    python youtube_upload.py [--config CONFIG_FILE] [--dry-run] [--no-fetch-list]
    （タイトル一致でスキップ判定。data/uploaded_from_youtube.txt を参照・追記）
"""

import os
import sys
import json
import logging
from typing import Dict, Set
from pathlib import Path

# utilsディレクトリをパスに追加（親ディレクトリからインポートできるように）
parent_dir = Path(__file__).parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# ユーティリティモジュールをインポート
from utils import auth
from utils import file_utils
from utils import paths
from utils import playlist
from utils import upload
from utils import youtube_list

# ログ設定
logs_dir = paths.ensure_logs_dir()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(logs_dir / 'youtube_upload.log'), encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)

# ログのバッファリングを無効化
for handler in logger.handlers:
    if isinstance(handler, logging.FileHandler):
        handler.setLevel(logging.INFO)


def _write_upload_runs_md(md_path: Path, runs: list) -> None:
    """アップロード実行ログを人が確認しやすい Markdown で書き出す。"""
    lines = [
        "# YouTube アップロード実行ログ（人が確認用）",
        "",
        "JSON は `upload_runs.json` を参照。",
        "",
    ]
    for i, r in enumerate(reversed(runs)):  # 新しい実行が上に来る
        date = (r.get("date") or "")[:19].replace("T", " ")
        dir_path = r.get("dir", "")
        year = r.get("year", "")
        dry = r.get("dry_run", False)
        s = r.get("success", 0)
        f = r.get("failed", 0)
        sk = r.get("skipped", 0)
        pl = r.get("playlist_added", 0)
        lines.append(f"## 実行 {len(runs) - i} — {date}")
        lines.append("")
        lines.append(f"- **対象**: `{dir_path}`")
        if year:
            lines.append(f"- **年**: {year}")
        lines.append(f"- **ドライラン**: {'はい' if dry else 'いいえ'}")
        lines.append(f"- **成功**: {s} / **失敗**: {f} / **スキップ**: {sk} / **プレイリスト追加**: {pl}")
        lines.append("")
        lines.append("---")
        lines.append("")
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info(f"Recorded human-readable log to {md_path}")
    except Exception as e:
        logger.warning(f"Failed to write upload_runs.md: {e}")


def upload_dir_movies(
    dir_path: str,
    description: str,
    privacy_status: str = "private",
    category_id: str = "22",
    upload_mode: str = "simple",
    auto_add_to_playlist: bool = True,
    auto_sort_playlist: bool = True,
    dry_run: bool = False,
    fetch_uploaded_list: bool = True,
) -> dict:
    """
    ディレクトリ内の動画のうち、YouTube にまだないものだけをアップロードします。
    スキップ判定はタイトルのみ（data/uploaded_from_youtube.txt を参照・成功時に追記）。
    fetch_uploaded_list=True（既定）: 起動時に API でアップロード済み一覧を取得し、その結果を data/uploaded_from_youtube.txt に保存。
    fetch_uploaded_list=False: ローカルの data/uploaded_from_youtube.txt のみ参照（API 取得スキップで短時間開始）。
    """
    if dry_run:
        logger.info("=" * 80)
        logger.info("DRY RUN MODE - 実際にはアップロードしません")
        logger.info("=" * 80)
    
    # 1. 認証（アップロード時はADMIN、dry-run時はAPI一覧取得のみでREADONLY）
    youtube_upload = None
    youtube_admin = None
    try:
        if dry_run:
            youtube_admin = auth.get_authenticated_service(scope=auth.YOUTUBE_READONLY_SCOPE)
            youtube_upload = youtube_admin
        else:
            youtube_upload = auth.get_authenticated_service(scope=auth.YOUTUBE_ADMIN_SCOPE)
            youtube_admin = youtube_upload
    except Exception as e:
        logger.error(f"Failed to authenticate: {e}")
        return {'success': 0, 'failed': 0, 'skipped': 0, 'playlist_added': 0}
    
    # 2. アップロード済み一覧を取得（API取得 or ローカルファイル）
    paths.ensure_data_dir()
    uploaded_from_youtube_path = paths.UPLOADED_FROM_YOUTUBE_PATH

    # fetch失敗時の安全策として、既存ローカル一覧を先に保持しておく
    local_uploaded_titles = set()
    if uploaded_from_youtube_path.exists():
        with open(uploaded_from_youtube_path, 'r', encoding='utf-8') as f:
            local_uploaded_titles = {line.strip() for line in f if line.strip()}

    if fetch_uploaded_list:
        logger.info("Fetching uploaded video list from YouTube API...")
        try:
            videos = youtube_list.get_upload_titles(youtube=youtube_admin)
            uploaded_titles = {v['snippet']['title'] for v in videos}
            # API取得結果が空で、かつローカルに実績がある場合は異常とみなして中断する
            if not uploaded_titles and local_uploaded_titles:
                logger.error(
                    "Fetched uploaded list is empty while local list has entries. "
                    "Aborting to avoid accidental duplicate uploads."
                )
                logger.error(
                    f"Local list: {uploaded_from_youtube_path} ({len(local_uploaded_titles)} titles)"
                )
                logger.error("Use --no-fetch-list temporarily and retry API list fetch later.")
                return {'success': 0, 'failed': 0, 'skipped': 0}
            logger.info(f"Got {len(uploaded_titles)} uploaded video(s) from YouTube API")
            with open(uploaded_from_youtube_path, 'w', encoding='utf-8') as f:
                for t in sorted(uploaded_titles):
                    f.write(t + '\n')
            logger.info(f"Saved to {uploaded_from_youtube_path}")
        except Exception as e:
            logger.error(f"Failed to fetch uploaded list from YouTube API: {e}")
            return {'success': 0, 'failed': 0, 'skipped': 0}
    else:
        # ローカルに保存した一覧を参照（API取得スキップ）
        if uploaded_from_youtube_path.exists():
            with open(uploaded_from_youtube_path, 'r', encoding='utf-8') as f:
                uploaded_titles = {line.strip() for line in f if line.strip()}
            logger.info(f"Using local list: {uploaded_from_youtube_path} ({len(uploaded_titles)} titles)")
        else:
            uploaded_titles = set()
            logger.info(f"Local list not found: {uploaded_from_youtube_path}, starting with empty list")
    
    # 動画ファイルを取得
    if not os.path.exists(dir_path):
        logger.error(f"Directory not found: {dir_path}")
        return {'success': 0, 'failed': 0, 'skipped': 0}

    target_movies = [
        f for f in os.listdir(dir_path)
        if os.path.isfile(os.path.join(dir_path, f)) and file_utils.is_video_file(f)
    ]

    if not target_movies:
        logger.info(f"No video files found in {dir_path}")
        return {'success': 0, 'failed': 0, 'skipped': 0}

    logger.info(f"Found {len(target_movies)} video file(s) in {dir_path}")

    # 統計情報
    stats = {'success': 0, 'failed': 0, 'skipped': 0, 'playlist_added': 0}
    
    # 年ごとのプレイリストIDをキャッシュ
    playlist_cache: Dict[str, str] = {}

    # アップロード
    for idx, movie_name in enumerate(target_movies, 1):
        logger.info(f"Processing {idx}/{len(target_movies)}: {movie_name}")
        
        movie_path = os.path.join(dir_path, movie_name)
        
        movie_title = file_utils.modify_movie_name(movie_name)
        if movie_title is None:
            stats['failed'] += 1
            continue
        
        # タイトルベースの重複チェック
        if movie_title in uploaded_titles:
            logger.info(f"Skipping already uploaded (by title): {movie_title}")
            stats['skipped'] += 1
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would upload: {movie_title} ({movie_path})")
            year = file_utils.extract_year_from_filename(movie_name)
            if year:
                logger.info(f"  Would add to playlist: {year}")
            stats['success'] += 1
            continue

        logger.info(f"Uploading: {movie_title} ({movie_path})")
        
        try:
            video_id = upload.initialize_upload(
                youtube_upload, movie_title, movie_path, description,
                privacy_status, category_id, upload_mode=upload_mode
            )
            
            if video_id:
                uploaded_titles.add(movie_title)
                try:
                    with open(uploaded_from_youtube_path, 'a', encoding='utf-8') as f:
                        f.write(movie_title + '\n')
                except Exception as e:
                    logger.warning(f"Failed to append to local list {uploaded_from_youtube_path}: {e}")
                logger.info(f"Successfully uploaded: {movie_title} (ID: {video_id})")
                
                # 再生リストに自動追加
                if auto_add_to_playlist and youtube_admin:
                    year = file_utils.extract_year_from_filename(movie_name)
                    if year:
                        # プレイリストIDを取得または作成
                        if year not in playlist_cache:
                            playlist_id = playlist.create_or_get_playlist(year, youtube_admin)
                            if playlist_id:
                                playlist_cache[year] = playlist_id
                                logger.info(f"Cached playlist ID for {year}: {playlist_id}")
                            else:
                                logger.warning(f"Failed to get/create playlist for year {year}")
                                year = None
                        
                        if year and year in playlist_cache:
                            playlist_id = playlist_cache[year]
                            logger.info(f"Adding video {video_id} to playlist {year} (ID: {playlist_id})")
                            if playlist.add_video_to_playlist(video_id, playlist_id, youtube_admin):
                                stats['playlist_added'] += 1
                                logger.info(f"Successfully added video to playlist: {year}")
                            else:
                                logger.warning(f"Failed to add video to playlist: {year}")
                        else:
                            logger.warning(f"Playlist ID not found in cache for year {year}")
                    else:
                        logger.warning(f"Could not extract year from filename: {movie_name}")
                
                # ログを即座に書き込む
                for handler in logger.handlers:
                    handler.flush()
                stats['success'] += 1
            else:
                logger.error(f"Upload failed: {movie_title}")
                stats['failed'] += 1
                
        except Exception as e:
            logger.error(f"An error occurred while uploading {movie_title}: {e}")
            stats['failed'] += 1
    
    if not dry_run:
        # 対象年 = 追加したプレイリスト + 対象フォルダの年
        years_to_sort = set(playlist_cache.keys())
        year_from_dir = file_utils.extract_year_from_dir_path(dir_path)
        if year_from_dir:
            years_to_sort.add(year_from_dir)

        if youtube_admin and years_to_sort:
            # 再生リストの重複を削除（先頭を残し2件目以降を削除）
            logger.info("Removing duplicate videos from playlists...")
            for year in sorted(years_to_sort):
                playlist_id = playlist_cache.get(year)
                if not playlist_id:
                    playlist_id = playlist.create_or_get_playlist(year, youtube_admin)
                if playlist_id:
                    try:
                        removed = playlist.remove_duplicate_playlist_items(playlist_id, youtube_admin)
                        if removed > 0:
                            logger.info(f"Removed {removed} duplicate(s) from playlist {year}")
                    except Exception as e:
                        logger.warning(f"Failed to remove duplicates from playlist {year}: {e}")

            # 再生リストを撮影日順にソート
            if auto_sort_playlist:
                logger.info("Sorting playlists by date...")
                for year in sorted(years_to_sort):
                    playlist_id = playlist_cache.get(year)
                    if not playlist_id:
                        playlist_id = playlist.create_or_get_playlist(year, youtube_admin)
                    if playlist_id:
                        try:
                            playlist.sort_playlist_by_date(playlist_id, youtube_admin)
                        except Exception as e:
                            logger.warning(f"Failed to sort playlist {year}: {e}")
    else:
        logger.info("[DRY RUN] Skipping post-upload operations (list update, playlist sort)")

    logger.info(f"\nUpload completed:")
    logger.info(f"  Success: {stats['success']}")
    logger.info(f"  Failed: {stats['failed']}")
    logger.info(f"  Skipped: {stats['skipped']}")
    if stats.get('playlist_added', 0) > 0:
        logger.info(f"  Playlist added: {stats['playlist_added']}")
    return stats


def load_config(config_file: str = "config.json") -> dict:
    """
    設定ファイルを読み込みます。
    
    Args:
        config_file: 設定ファイルのパス
        
    Returns:
        設定の辞書
    """
    default_config = {
        "target_dir": "G:/Users/chiyo/Pictures/movie/2025/",
        "movie_tag": "2025年",
        "privacy_status": "private",
        "category_id": "22",
        "upload_mode": "simple",
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
                logger.info(f"Loaded config from {config_file}")
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}. Using defaults.")
    else:
        logger.info(f"Config file not found: {config_file}. Using defaults.")
    
    return default_config


if __name__ == '__main__':
    # 起動直後に表示（バッファで止まって見えない問題を防ぐ）
    import argparse
    import locale
    print("YouTube upload script starting...", flush=True)

    # 文字エンコーディングの問題を回避するため、sys.argvをデコード
    try:
        system_encoding = locale.getpreferredencoding()
        decoded_argv = []
        for arg in sys.argv:
            if isinstance(arg, bytes):
                try:
                    decoded_argv.append(arg.decode(system_encoding))
                except:
                    try:
                        decoded_argv.append(arg.decode('utf-8'))
                    except:
                        decoded_argv.append(arg.decode('cp932', errors='replace'))
            else:
                decoded_argv.append(arg)
        sys.argv = decoded_argv
    except Exception as e:
        logger.warning(f"Failed to decode command line arguments: {e}")
    
    # まず、独自の引数を抽出
    custom_args = []
    oauth_args = []
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ['--config', '--dir', '--tag', '--dry-run', '--no-fetch-list', '--upload-mode']:
            custom_args.append(arg)
            if arg in ['--dry-run', '--no-fetch-list']:
                i += 1
            elif i + 1 < len(sys.argv):
                value = sys.argv[i + 1]
                if isinstance(value, str):
                    custom_args.append(value)
                else:
                    for encoding in ['utf-8', 'cp932', 'shift_jis', 'latin-1']:
                        try:
                            custom_args.append(value.decode(encoding))
                            break
                        except:
                            continue
                    else:
                        custom_args.append(str(value))
                i += 2
            else:
                i += 1
        else:
            oauth_args.append(arg)
            i += 1
    
    # 独自の引数をパース
    parser = argparse.ArgumentParser(description='Upload videos to YouTube')
    parser.add_argument('--config', default='config.json', help='Config file path')
    parser.add_argument('--dir', help='Target directory (overrides config)')
    parser.add_argument('--tag', help='Movie tag/description (overrides config)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no actual upload)')
    parser.add_argument('--no-fetch-list', action='store_true', help='Do not fetch uploaded list from YouTube API; use local data/uploaded_from_youtube.txt and append on success')
    parser.add_argument('--upload-mode', choices=['simple', 'resumable', 'auto'], help='Upload mode: simple, resumable, or auto')
    
    args, unknown = parser.parse_known_args(custom_args)
    
    # oauth2client用の引数をsys.argvに復元
    sys.argv = [sys.argv[0]] + oauth_args

    # 設定の読み込み
    config = load_config(args.config)
    
    # コマンドライン引数で上書き
    target_dir = args.dir if args.dir else config['target_dir']
    
    # 説明文をフォルダ名（年）から自動生成
    year_from_dir = file_utils.extract_year_from_dir_path(target_dir)
    if year_from_dir:
        movie_tag = f"{year_from_dir}年"
        logger.info(f"Auto-generated description from directory: {movie_tag}")
    elif args.tag:
        try:
            if '' in args.tag or '\ufffd' in args.tag:
                logger.warning(f"Detected corrupted characters in tag. Using config file value instead.")
                movie_tag = config['movie_tag']
            else:
                movie_tag = args.tag
        except:
            movie_tag = config['movie_tag']
    else:
        movie_tag = config['movie_tag']
    
    privacy_status = config['privacy_status']
    category_id = config['category_id']
    upload_mode = args.upload_mode if args.upload_mode else config.get('upload_mode', 'simple')
    if upload_mode not in upload.VALID_UPLOAD_MODES:
        logger.warning(f"Invalid upload mode '{upload_mode}' in config/args. Falling back to simple.")
        upload_mode = "simple"

    logger.info("=" * 80)
    logger.info("YouTube Upload Script")
    logger.info(f"Target directory: {target_dir}")
    logger.info(f"Movie tag: {movie_tag}")
    logger.info(f"Privacy status: {privacy_status}")
    logger.info(f"Category ID: {category_id}")
    logger.info(f"Upload mode: {upload_mode}")
    logger.info("=" * 80)

    # アップロード実行
    try:
        stats = upload_dir_movies(
            target_dir,
            movie_tag,
            privacy_status,
            category_id,
            upload_mode=upload_mode,
            auto_add_to_playlist=True,
            auto_sort_playlist=True,
            dry_run=args.dry_run,
            fetch_uploaded_list=not args.no_fetch_list,
        )
        logger.info(f"Final stats: {stats}")

        # 実行結果を data/upload_runs.json に追記
        paths.ensure_data_dir()
        from datetime import datetime
        run_entry = {
            "date": datetime.now().isoformat(),
            "dir": target_dir,
            "year": year_from_dir,
            "dry_run": args.dry_run,
            "upload_mode": upload_mode,
            "success": stats.get("success", 0),
            "failed": stats.get("failed", 0),
            "skipped": stats.get("skipped", 0),
            "playlist_added": stats.get("playlist_added", 0),
        }
        upload_runs_path = paths.DATA_DIR / "upload_runs.json"
        runs = []
        if upload_runs_path.exists():
            try:
                with open(upload_runs_path, "r", encoding="utf-8") as f:
                    runs = json.load(f)
                    if not isinstance(runs, list):
                        runs = [runs]
            except Exception:
                runs = []
        runs.append(run_entry)
        with open(upload_runs_path, "w", encoding="utf-8") as f:
            json.dump(runs, f, ensure_ascii=False, indent=2)
        logger.info(f"Recorded run to {upload_runs_path}")
        # 人が確認しやすい Markdown も出力
        _write_upload_runs_md(paths.DATA_DIR / "upload_runs.md", runs)
    except KeyboardInterrupt:
        logger.info("Upload interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
