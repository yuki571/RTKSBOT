@echo off
title Discord Bot - System Service
color 0A

echo.
echo ===============================================
echo        Discord Bot - System Service
echo ===============================================
echo.

cd /d "%~dp0"

REM 管理者権限チェック
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 管理者権限が必要です。
    echo 右クリック→「管理者として実行」でお試しください。
    pause
    exit /b 1
)

REM Python仮想環境の確認
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] 仮想環境が見つかりません。
    echo 先にセットアップを完了してください。
    pause
    exit /b 1
)

echo [INFO] システムサービスとして起動します...
echo [INFO] Ctrl+C で停止できます
echo.

REM 無限ループで再起動
:restart
echo [%date% %time%] Starting Discord Bot...

REM サービスラッパーを実行
".venv\Scripts\python.exe" service_wrapper.py

REM 異常終了の場合
echo.
echo [WARNING] Bot service stopped unexpectedly
echo [INFO] Restarting in 10 seconds...
echo [INFO] Press Ctrl+C to cancel restart
timeout /t 10 /nobreak >nul 2>&1

goto restart