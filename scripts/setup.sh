#!/bin/bash
# RTKS Discord Bot - 自動セットアップスクリプト (Linux/macOS)

set -e  # エラー時に停止

echo "===================================="
echo "  RTKS Discord Bot - 自動セットアップ"
echo "===================================="
echo

# Python インストール確認
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 がインストールされていません。"
    echo "📥 Python 3.8以上をインストールしてください"
    exit 1
fi

echo "✅ Python が見つかりました"
python3 --version

# Git インストール確認
if ! command -v git &> /dev/null; then
    echo "⚠️  Git がインストールされていませんが、続行します"
else
    echo "✅ Git が見つかりました"
fi

echo
echo "🚀 セットアップを開始します..."
echo

# 仮想環境作成
echo "📦 仮想環境を作成しています..."
if [ -d ".venv" ]; then
    echo "⚠️  既存の仮想環境を削除します"
    rm -rf .venv
fi

python3 -m venv .venv

# 仮想環境アクティベート
echo "🔄 仮想環境をアクティベートしています..."
source .venv/bin/activate

# pip アップグレード
echo "📋 pip をアップグレードしています..."
python -m pip install --upgrade pip

# 依存関係インストール
echo "📚 依存関係をインストールしています..."
pip install -r requirements.txt

# 設定ファイルのコピー
echo "⚙️  設定ファイルを準備しています..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ .env ファイルを作成しました"
    else
        echo "📝 .env.example から .env を作成してください"
    fi
else
    echo "✅ .env ファイルが既に存在します"
fi

if [ ! -f "config.py" ]; then
    if [ -f "config.example.py" ]; then
        cp config.example.py config.py
        echo "✅ config.py ファイルを作成しました"
    else
        echo "📝 config.example.py から config.py を作成してください"
    fi
else
    echo "✅ config.py ファイルが既に存在します"
fi

# FFmpeg確認
echo "🎵 FFmpeg インストール確認..."
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg がインストールされていません"
    echo "📥 音楽機能を使用する場合は FFmpeg をインストールしてください"
    echo "   Ubuntu/Debian: sudo apt install ffmpeg"
    echo "   macOS: brew install ffmpeg"
else
    echo "✅ FFmpeg が見つかりました"
fi

# 実行権限付与
echo "🔐 実行権限を設定しています..."
chmod +x start_bot.sh 2>/dev/null || echo "start_bot.sh が見つかりません"

echo
echo "===================================="
echo "🎉 セットアップ完了！"
echo "===================================="
echo
echo "📋 次の手順:"
echo "1. .env ファイルにDiscordボットトークンを設定"
echo "2. config.py で必要な設定を調整"
echo "3. ./start_bot.sh でボットを起動"
echo
echo "📖 詳細な設定方法は README.md をご確認ください"
echo