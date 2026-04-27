@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "VENV_PYTHON=..\.venv311\Scripts\python.exe"
if not exist "%VENV_PYTHON%" set "VENV_PYTHON=..\.venv\Scripts\python.exe"

echo.
echo  写真・動画ツール UI を起動しています...
echo  ブラウザは少し待ってから開きます。
echo  終了するときはこの窓で Ctrl+C を押すか、窓を閉じてください。
echo.

start /b cmd /c "timeout /t 3 >nul && start http://127.0.0.1:5151"

if exist "%VENV_PYTHON%" (
  "%VENV_PYTHON%" app.py
) else (
  python app.py
)

pause
