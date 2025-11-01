#!/bin/bash
# RTKS Discord Bot - 起動スクリプト (Linux/macOS)

set -e

echo "===================================="
echo "  RTKS Discord Bot - 起動スクリプト"
echo "===================================="
echo

# 仮想環境の確認
if [ ! -f ".venv/bin/activate" ]; then
    echo "❌ 仮想環境が見つかりません。"
    echo "📥 setup.sh を先に実行してください。"
    exit 1
fi

# 仮想環境アクティベート
echo "🔄 仮想環境をアクティベートしています..."
source .venv/bin/activate

# .env ファイル確認
if [ ! -f ".env" ]; then
    echo "❌ .env ファイルが見つかりません。"
    echo "📝 .env.example をコピーして .env を作成し、設定を行ってください。"
    exit 1
fi

# config.py ファイル確認
if [ ! -f "config.py" ]; then
    echo "❌ config.py ファイルが見つかりません。"
    echo "📝 config.example.py をコピーして config.py を作成し、設定を行ってください。"
    exit 1
fi

# ボット起動
echo "🚀 ボットを起動しています..."
echo "===================================="
python bot.py

echo
echo "===================================="
echo "🔄 ボットが終了しました"
echo "===================================="