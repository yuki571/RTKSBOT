@echo off
echo VOICEVOXを起動中...

REM VOICEVOXの一般的なインストールパス
set VOICEVOX_PATH=""

REM 可能な場所を順番にチェック
if exist "C:\Users\%USERNAME%\AppData\Local\Programs\VOICEVOX\VOICEVOX.exe" (
    set VOICEVOX_PATH="C:\Users\%USERNAME%\AppData\Local\Programs\VOICEVOX\VOICEVOX.exe"
)

if exist "C:\Program Files\VOICEVOX\VOICEVOX.exe" (
    set VOICEVOX_PATH="C:\Program Files\VOICEVOX\VOICEVOX.exe"
)

if exist "C:\Program Files (x86)\VOICEVOX\VOICEVOX.exe" (
    set VOICEVOX_PATH="C:\Program Files (x86)\VOICEVOX\VOICEVOX.exe"
)

if %VOICEVOX_PATH%=="" (
    echo ❌ VOICEVOXが見つかりません
    echo 以下のいずれかの場所にインストールしてください:
    echo   - C:\Users\%USERNAME%\AppData\Local\Programs\VOICEVOX\
    echo   - C:\Program Files\VOICEVOX\
    echo   - C:\Program Files (x86)\VOICEVOX\
    pause
    exit /b 1
)

echo ✅ VOICEVOX起動: %VOICEVOX_PATH%
start "" %VOICEVOX_PATH%

echo ⏳ VOICEVOXサーバーの起動を待機中...
timeout /t 5 /nobreak >nul

echo ✅ VOICEVOX起動完了
echo localhost:50021でサーバーが動作しています
echo.
echo このウィンドウは閉じても構いません
pause