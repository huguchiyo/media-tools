@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "APP_PYTHON=..\.venv\Scripts\python.exe"
if not exist "..\.venv\pyvenv.cfg" set "APP_PYTHON=..\.venv311\Scripts\python.exe"
if not exist "%APP_PYTHON%" set "APP_PYTHON=python"

echo.
echo  写真・動画ツール UI を起動しています...
echo  使用する Python: %APP_PYTHON%
echo  ブラウザは少し待ってから開きます。
echo.
echo  終了するときはこの窓で Ctrl キーと C キーを押すか、窓を閉じてください。
echo.

echo  必要な Python 依存を確認しています...
"%APP_PYTHON%" -c "import flask, httplib2, google_auth_oauthlib" >nul 2>nul
if errorlevel 1 (
  echo  依存が不足しているため、この Python 環境にインストールします...
  "%APP_PYTHON%" -m pip install -r requirements.txt
  if errorlevel 1 goto :install_failed
  "%APP_PYTHON%" -m pip install google-api-python-client google-auth-oauthlib httplib2
  if errorlevel 1 goto :install_failed
) else (
  echo  Python 依存は揃っています。
)
echo.

start /b cmd /c "timeout /t 3 >nul && start http://127.0.0.1:5151"

"%APP_PYTHON%" app.py

pause
goto :eof

:install_failed
echo.
echo  依存インストールに失敗しました。
echo  次のコマンドを、上に表示された Python で実行してください：
echo    %APP_PYTHON% -m pip install -r requirements.txt
echo    %APP_PYTHON% -m pip install google-api-python-client google-auth-oauthlib httplib2
echo.
pause
exit /b 1
