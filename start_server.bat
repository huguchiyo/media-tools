@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  Tools 配下の「写真・動画ツール」UI を起動します。
echo.

call "%~dp0photo_video_ui\start_server.bat"
