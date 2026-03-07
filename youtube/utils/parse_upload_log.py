#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youtube_upload.log から直近のアップロード実行の詳細を抽出するユーティリティ。

利用例:
  from utils.parse_upload_log import get_last_upload_run_details
  details = get_last_upload_run_details()
  # => {"date": "...", "target_dir": "...", "uploaded": [...], "skipped": [...], "failed": [...]}
"""

import re
import json
from pathlib import Path
from typing import Optional

# プロジェクトルート（Tools/youtube/）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = _PROJECT_ROOT / "logs" / "youtube_upload.log"

# ログ行のパターン（時刻 - レベル - メッセージ）
# Successfully uploaded: タイトル (ID: video_id)
RE_SUCCESS = re.compile(r"Successfully uploaded:\s*(.+?)\s*\(ID:\s*([a-zA-Z0-9_-]+)\)")
# Skipping already uploaded (by title): タイトル
RE_SKIP = re.compile(r"Skipping already uploaded \(by title\):\s*(.+)")
# Upload failed: タイトル
RE_FAIL = re.compile(r"Upload failed:\s*(.+)")
# An error occurred while uploading タイトル: エラー内容
RE_ERROR = re.compile(r"An error occurred while uploading\s*(.+?):\s*(.+)")
# [DRY RUN] Would upload: タイトル
RE_DRY_RUN = re.compile(r"\[DRY RUN\] Would upload:\s*(.+?)\s*\(")


def _extract_message(line: str) -> Optional[str]:
    """ログ行からメッセージ部分を抽出。形式: 日時 - レベル - メッセージ"""
    if " - INFO - " in line:
        return line.split(" - INFO - ", 1)[-1].strip()
    if " - WARNING - " in line:
        return line.split(" - WARNING - ", 1)[-1].strip()
    if " - ERROR - " in line:
        return line.split(" - ERROR - ", 1)[-1].strip()
    return None


def get_last_upload_run_details(log_path: Optional[Path] = None) -> Optional[dict]:
    """
    youtube_upload.log の直近1回の実行について、詳細を返す。

    Returns:
        {
            "date": "YYYY-MM-DD HH:MM:SS",
            "target_dir": "...",
            "dry_run": bool,
            "uploaded": [{"title": "...", "video_id": "..."}, ...],
            "skipped": [{"title": "..."}, ...],
            "failed": [{"title": "...", "error": "..."}, ...],
            "summary": {"success": n, "failed": n, "skipped": n}
        }
        ログが空または解析できない場合は None
    """
    log_path = log_path or DEFAULT_LOG_PATH
    if not log_path.exists():
        return None

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # 最後の実行ブロックを特定: "YouTube Upload Script" の次に "Target directory:" が来るブロック
    run_start = -1
    run_date = None
    target_dir = None
    dry_run = False

    for i in range(len(lines) - 1, -1, -1):
        msg = _extract_message(lines[i])
        if not msg:
            continue
        if "Final stats:" in msg or "Upload complete." in msg:
            # この実行の終端。この行の日時を取得
            parts = lines[i].split(" - ", 2)
            if len(parts) >= 1:
                run_date = parts[0].strip()
            # さかのぼって "Target directory:" を探す
            for j in range(i - 1, max(-1, i - 30), -1):
                m = _extract_message(lines[j])
                if m and "Target directory:" in m:
                    target_dir = m.replace("Target directory:", "").strip()
                if m and "YouTube Upload Script" in m:
                    run_start = j
                    if j > 0:
                        run_date = lines[j].split(" - ", 1)[0].strip()
                    break
            if run_start >= 0:
                break
    if run_start < 0:
        return None

    uploaded = []
    skipped = []
    failed = []

    for idx in range(run_start, len(lines)):
        msg = _extract_message(lines[idx])
        if not msg:
            continue
        if "YouTube Upload Script" in msg and idx > run_start:
            # 次の実行開始で終了
            break
        if "Upload complete." in msg or "Final stats:" in msg:
            break

        m = RE_SUCCESS.search(msg)
        if m:
            uploaded.append({"title": m.group(1).strip(), "video_id": m.group(2).strip()})
            continue
        m = RE_SKIP.search(msg)
        if m:
            skipped.append({"title": m.group(1).strip()})
            continue
        m = RE_FAIL.search(msg)
        if m:
            failed.append({"title": m.group(1).strip(), "error": "Upload failed"})
            continue
        m = RE_ERROR.search(msg)
        if m:
            failed.append({"title": m.group(1).strip(), "error": m.group(2).strip()})
            continue
        if "[DRY RUN] Would upload:" in msg:
            dry_run = True
            m = RE_DRY_RUN.search(msg)
            if m:
                uploaded.append({"title": m.group(1).strip(), "video_id": "(dry run)"})

    return {
        "date": run_date or "",
        "target_dir": target_dir or "",
        "dry_run": dry_run,
        "uploaded": uploaded,
        "skipped": skipped,
        "failed": failed,
        "summary": {
            "success": len(uploaded),
            "failed": len(failed),
            "skipped": len(skipped),
        },
    }


def main():
    """CLI: 直近実行の詳細を JSON で標準出力に出す。"""
    details = get_last_upload_run_details()
    if details is None:
        print("{}")
        return
    print(json.dumps(details, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
