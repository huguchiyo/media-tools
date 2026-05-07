#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo
echo " Tools 配下の「写真・動画ツール」UI を起動します。"
echo

exec "$SCRIPT_DIR/photo_video_ui/start_server.command"
