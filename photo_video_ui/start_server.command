#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

APP_PYTHON="../.venv/bin/python3"
if [ ! -f "../.venv/pyvenv.cfg" ] && [ -f "../.venv311/bin/python3" ]; then
  APP_PYTHON="../.venv311/bin/python3"
fi
if [ ! -x "$APP_PYTHON" ]; then
  APP_PYTHON="python3"
fi

echo
echo " 写真・動画ツール UI を起動しています..."
echo " 使用する Python: $APP_PYTHON"
echo " ブラウザは少し待ってから開きます。"
echo
echo " 終了するときはこのウィンドウで Ctrl+C を押してください。"
echo

echo " 必要な Python 依存を確認しています..."
"$APP_PYTHON" -c "import flask, httplib2, google_auth_oauthlib" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo " 依存が不足しているため、この Python 環境にインストールします..."
  "$APP_PYTHON" -m pip install -r requirements.txt || {
    echo
    echo " 依存インストールに失敗しました。"
    echo " 次のコマンドを実行してください:"
    echo "   $APP_PYTHON -m pip install -r requirements.txt"
    echo "   $APP_PYTHON -m pip install google-api-python-client google-auth-oauthlib httplib2"
    echo
    read -r -p "Enter キーで終了します..."
    exit 1
  }
  "$APP_PYTHON" -m pip install google-api-python-client google-auth-oauthlib httplib2 || {
    echo
    echo " 依存インストールに失敗しました。"
    echo " 次のコマンドを実行してください:"
    echo "   $APP_PYTHON -m pip install google-api-python-client google-auth-oauthlib httplib2"
    echo
    read -r -p "Enter キーで終了します..."
    exit 1
  }
else
  echo " Python 依存は揃っています。"
fi
echo

( sleep 3; open "http://127.0.0.1:5151" ) >/dev/null 2>&1 &

"$APP_PYTHON" app.py
EXIT_CODE=$?
echo
read -r -p "Enter キーで終了します..."
exit $EXIT_CODE
