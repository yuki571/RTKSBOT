@echo off
title Discord Bot Auto Restart
cd /d "%~dp0"

:start
echo.
echo ========================================
echo Discord Bot Starting... [%date% %time%]
echo ========================================

REM ボット実行
".venv\Scripts\python.exe" bot.py

REM 終了コードをチェック
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Bot exited normally. [%date% %time%]
    echo ========================================
    pause
    exit /b 0
) else (
    echo.
    echo ========================================
    echo Bot crashed! [%date% %time%]
    echo Restarting in 10 seconds...
    echo ========================================
    timeout /t 10 /nobreak
    goto start
)