@echo off
chcp 65001 > nul
echo ====================================
echo   RTKS Discord Bot - 自動セットアップ
echo ====================================
echo.

:: Python インストール確認
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Python がインストールされていません。
    echo 📥 Python 3.8以上をインストールしてください: https://python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python が見つかりました
python --version

:: Git インストール確認
git --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ⚠️  Git がインストールされていませんが、続行します
) else (
    echo ✅ Git が見つかりました
)

echo.
echo 🚀 セットアップを開始します...
echo.

:: 仮想環境作成
echo 📦 仮想環境を作成しています...
if exist ".venv" (
    echo ⚠️  既存の仮想環境を削除します
    rmdir /s /q ".venv"
)

python -m venv .venv
if %ERRORLEVEL% neq 0 (
    echo ❌ 仮想環境の作成に失敗しました
    pause
    exit /b 1
)

:: 仮想環境アクティベート
echo 🔄 仮想環境をアクティベートしています...
call .venv\Scripts\activate.bat

:: pip アップグレード
echo 📋 pip をアップグレードしています...
python -m pip install --upgrade pip

:: 依存関係インストール
echo 📚 依存関係をインストールしています...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo ❌ 依存関係のインストールに失敗しました
    pause
    exit /b 1
)

:: 設定ファイルのコピー
echo ⚙️  設定ファイルを準備しています...
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env"
        echo ✅ .env ファイルを作成しました
    ) else (
        echo 📝 .env.example から .env を作成してください
    )
) else (
    echo ✅ .env ファイルが既に存在します
)

if not exist "config.py" (
    if exist "config.example.py" (
        copy "config.example.py" "config.py"
        echo ✅ config.py ファイルを作成しました
    ) else (
        echo 📝 config.example.py から config.py を作成してください
    )
) else (
    echo ✅ config.py ファイルが既に存在します
)

:: FFmpeg確認
echo 🎵 FFmpeg インストール確認...
ffmpeg -version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ⚠️  FFmpeg がインストールされていません
    echo 📥 音楽機能を使用する場合は FFmpeg をインストールしてください
    echo    ダウンロード: https://ffmpeg.org/download.html
) else (
    echo ✅ FFmpeg が見つかりました
)

echo.
echo ====================================
echo 🎉 セットアップ完了！
echo ====================================
echo.
echo 📋 次の手順:
echo 1. .env ファイルにDiscordボットトークンを設定
echo 2. config.py で必要な設定を調整
echo 3. start_bot.bat でボットを起動
echo.
echo 📖 詳細な設定方法は README.md をご確認ください
echo.

pause