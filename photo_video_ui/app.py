#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
写真・動画ツール統合UI — Flask バックエンド

- 設定の読み書き・フォルダ選択（ネイティブダイアログ）
- 分離スクリプト実行とログのストリーミング
- アップロード実行とログのストリーミング
- 分離結果・アップロード結果の取得
"""

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

# プロジェクトルート（Tools/）
TOOLS_ROOT = Path(__file__).resolve().parent.parent
VIDEO_MOVE_SCRIPT = TOOLS_ROOT / "VideoMoveTools" / "move_videos_to_movie.py"
YOUTUBE_SCRIPT = TOOLS_ROOT / "youtube" / "youtube_upload.py"
YOUTUBE_DIR = TOOLS_ROOT / "youtube"
YOUTUBE_TOKEN_FILE = YOUTUBE_DIR / "youtube-admin-oauth2.json"
YOUTUBE_UTILS = TOOLS_ROOT / "youtube" / "utils"
MOVED_LOG_JSON = TOOLS_ROOT / "VideoMoveTools" / "moved_videos_log.json"
UPLOAD_RUNS_JSON = TOOLS_ROOT / "youtube" / "data" / "upload_runs.json"

DATA_DIR = Path(__file__).resolve().parent / "data"
SETTINGS_JSON = DATA_DIR / "settings.json"

DEFAULT_CAMERA = "G:/Users/chiyo/Pictures/camera"
DEFAULT_MOVIE = "G:/Users/chiyo/Pictures/movie"

app = Flask(__name__, static_folder="static", static_url_path="")


def load_settings():
    if not SETTINGS_JSON.exists():
        return {"pathCamera": DEFAULT_CAMERA, "pathMovie": DEFAULT_MOVIE}
    try:
        with open(SETTINGS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"pathCamera": DEFAULT_CAMERA, "pathMovie": DEFAULT_MOVIE}


def save_settings(settings):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_JSON, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def open_folder_dialog(initial_dir: str = None):
    """ネイティブのフォルダ選択ダイアログを開き、選択したパスを返す。"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(initialdir=initial_dir or os.path.expanduser("~"))
        root.destroy()
        return path or None
    except Exception as e:
        return None


def stream_process(script_path: Path, args: list, cwd: Path = None):
    """サブプロセスを実行し、stdout/stderr を1行ずつ yield する。"""
    cwd = cwd or script_path.parent
    cmd = [sys.executable, str(script_path)] + args
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            bufsize=1,
        )
        for line in iter(proc.stdout.readline, ""):
            yield line.rstrip("\n") or "\n"
        proc.wait()
    except Exception as e:
        yield f"Error: {e}\n"


# ---------- ルート ----------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    return jsonify(load_settings())


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.get_json() or {}
    s = load_settings()
    if "pathCamera" in data:
        s["pathCamera"] = data["pathCamera"]
    if "pathMovie" in data:
        s["pathMovie"] = data["pathMovie"]
    save_settings(s)
    return jsonify(s)


@app.route("/api/folder-picker", methods=["POST"])
def api_folder_picker():
    """ネイティブのフォルダ選択ダイアログを開き、選択したパスを返す。"""
    data = request.get_json() or {}
    initial = data.get("initialPath", "")
    path = open_folder_dialog(initial)
    if path is None:
        return jsonify({"ok": False, "path": None})
    return jsonify({"ok": True, "path": path})


def _last_move_result():
    """moved_videos_log.json の直近1件を返す。"""
    if not MOVED_LOG_JSON.exists():
        return None
    try:
        with open(MOVED_LOG_JSON, "r", encoding="utf-8") as f:
            log = json.load(f)
        if isinstance(log, list):
            entry = log[-1] if log else None
        else:
            entry = log
        if not entry:
            return None
        from datetime import datetime
        date = entry.get("date", "")
        if date and "T" in date:
            date = date.replace("T", " ")[:19]
        return {
            "date": date,
            "source": entry.get("source_dirs", [""])[0] if entry.get("source_dirs") else "",
            "target": entry.get("target_dir", ""),
            "count": entry.get("moved_count", 0),
            "rows": [
                {
                    "from": m.get("source", ""),
                    "to": m.get("dest", ""),
                    "year": m.get("year", ""),
                }
                for m in entry.get("moved_files", [])
            ],
        }
    except Exception:
        return None


@app.route("/api/separate/result", methods=["GET"])
def api_separate_result():
    result = _last_move_result()
    if result is None:
        return jsonify({"ok": False, "result": None})
    return jsonify({"ok": True, "result": result})


@app.route("/api/separate", methods=["POST"])
def api_separate():
    """分離を実行し、ログをストリーミングで返す。"""
    data = request.get_json() or {}
    source = (data.get("source") or "").strip() or DEFAULT_CAMERA
    target = (data.get("target") or "").strip() or DEFAULT_MOVIE
    dry_run = bool(data.get("dryRun", False))

    def generate():
        if dry_run:
            args = ["--source", source, "--target", target, "--dry-run"]
        else:
            # UI 側で確認済みのため常に --execute-yes（スクリプトの stdin 確認でブロックしない）
            args = ["--source", source, "--target", target, "--execute-yes"]
        for line in stream_process(VIDEO_MOVE_SCRIPT, args, cwd=TOOLS_ROOT):
            yield f"data: {json.dumps({'line': line})}\n\n"
        yield "data: {\"done\": true}\n\n"

    if not VIDEO_MOVE_SCRIPT.exists():
        return jsonify({"error": "move_videos_to_movie.py が見つかりません"}), 500
    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/movie-folders", methods=["GET"])
def api_movie_folders():
    """movie 直下のサブフォルダ名一覧を返す。"""
    s = load_settings()
    movie_path = Path(s.get("pathMovie", DEFAULT_MOVIE))
    if not movie_path.exists() or not movie_path.is_dir():
        return jsonify({"ok": True, "folders": []})
    folders = sorted(
        [d.name for d in movie_path.iterdir() if d.is_dir()],
        reverse=True,
    )
    return jsonify({"ok": True, "folders": folders})


def _upload_result_from_runs():
    """upload_runs.json の直近1件のサマリを返す。"""
    if not UPLOAD_RUNS_JSON.exists():
        return None
    try:
        with open(UPLOAD_RUNS_JSON, "r", encoding="utf-8") as f:
            runs = json.load(f)
        if not runs:
            return None
        r = runs[-1]
        date = (r.get("date") or "")[:19].replace("T", " ")
        return {
            "date": date,
            "dir": r.get("dir", ""),
            "year": r.get("year", ""),
            "success": r.get("success", 0),
            "failed": r.get("failed", 0),
            "skipped": r.get("skipped", 0),
            "playlist": r.get("playlist_added", 0),
        }
    except Exception:
        return None


def _upload_result_details():
    """parse_upload_log でログから詳細を取得。"""
    sys.path.insert(0, str(TOOLS_ROOT / "youtube"))
    try:
        from utils.parse_upload_log import get_last_upload_run_details
        return get_last_upload_run_details()
    except Exception:
        return None
    finally:
        if str(TOOLS_ROOT / "youtube") in sys.path:
            sys.path.remove(str(TOOLS_ROOT / "youtube"))


@app.route("/api/upload/result", methods=["GET"])
def api_upload_result():
    summary = _upload_result_from_runs()
    details = _upload_result_details()
    if summary is None and details is None:
        return jsonify({"ok": False, "summary": None, "details": None})
    out = {
        "ok": True,
        "summary": summary or {},
        "uploaded": (details or {}).get("uploaded", []),
        "skipped_list": [x.get("title", x) for x in (details or {}).get("skipped", [])],
        "failed_list": [
            {"title": x.get("title", ""), "error": x.get("error", "")}
            for x in (details or {}).get("failed", [])
        ],
    }
    if details and not summary:
        out["summary"] = {
            "date": details.get("date", ""),
            "dir": details.get("target_dir", ""),
            "year": "",
            "success": len(details.get("uploaded", [])),
            "failed": len(details.get("failed", [])),
            "skipped": len(details.get("skipped", [])),
            "playlist": 0,
        }
    return jsonify(out)


@app.route("/api/youtube-auth", methods=["POST"])
def api_youtube_auth():
    """
    YouTube OAuth 認証を行う。
    保存されているトークンを削除し、youtube_upload.py を実行して
    アップロード用スコープでブラウザログインを促す。
    ※ --dry-run は使わない（dry-run だと読み取り専用スコープになり、後で 403 になるため）。
    ※ 動画が入っていない「movie の直下」を --dir に指定し、実際のアップロードは行わない。
    """
    # 既存トークンを削除（invalid_grant / 403 対策）
    if YOUTUBE_TOKEN_FILE.exists():
        try:
            YOUTUBE_TOKEN_FILE.unlink()
        except OSError:
            pass

    s = load_settings()
    movie_path = (s.get("pathMovie") or DEFAULT_MOVIE).strip().rstrip("/\\")
    # movie 直下を指定（直下に動画ファイルがなければ 0 件で終了。アップロード用スコープで認証だけ行う）
    dir_path = movie_path

    def generate():
        yield f"data: {json.dumps({'line': 'OAuth トークンをリセットしました。'})}\n\n"
        yield f"data: {json.dumps({'line': 'ブラウザが開いたら Google でログインし、「許可」を押してアップロード権限を付与してください。'})}\n\n"
        yield f"data: {json.dumps({'line': '（movie 直下に動画はないため、この実行ではアップロードは行われません）'})}\n\n"
        for line in stream_process(YOUTUBE_SCRIPT, ["--dir", dir_path], cwd=YOUTUBE_DIR):
            yield f"data: {json.dumps({'line': line})}\n\n"
        yield "data: {\"done\": true}\n\n"

    if not YOUTUBE_SCRIPT.exists():
        return jsonify({"error": "youtube_upload.py が見つかりません"}), 500
    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """アップロードを実行し、ログをストリーミングで返す。"""
    data = request.get_json() or {}
    dir_path = (data.get("dir") or "").strip()
    dry_run = bool(data.get("dryRun", False))
    if not dir_path:
        return jsonify({"error": "dir を指定してください"}), 400

    def generate():
        args = ["--dir", dir_path, "--no-fetch-list"]
        if dry_run:
            args.append("--dry-run")
        for line in stream_process(YOUTUBE_SCRIPT, args, cwd=TOOLS_ROOT / "youtube"):
            yield f"data: {json.dumps({'line': line})}\n\n"
        yield "data: {\"done\": true}\n\n"

    if not YOUTUBE_SCRIPT.exists():
        return jsonify({"error": "youtube_upload.py が見つかりません"}), 500
    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host="127.0.0.1", port=5151, debug=True, threaded=True)
