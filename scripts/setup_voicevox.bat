@echo off
title VOICEVOX Setup for Discord Bot
color 0B

echo.
echo ===============================================
echo        VOICEVOX Setup for Discord Bot
echo ===============================================
echo.

echo 🤖 VOICEVOX（ゆっくりボイス）セットアップガイド
echo.
echo VOICEVOXは無料の音声合成ソフトウェアです。
echo Discord Botで「ずんだもん」「四国めたん」などの
echo 可愛い声で読み上げができるようになります！
echo.

echo ======== セットアップ手順 ========
echo.
echo 1. 公式サイトからVOICEVOXをダウンロード
echo    https://voicevox.hiroshiba.jp/
echo.
echo 2. インストール後、VOICEVOXを起動
echo.
echo 3. 設定でAPIサーバーを有効化
echo    - 設定（歯車アイコン）を開く
echo    - 「APIサーバー」タブを選択
echo    - 「APIサーバーを有効にする」にチェック
echo    - ポート番号: 50021 （デフォルト）
echo.
echo 4. Discordボットで音声コマンドが使用可能に！
echo.

echo ======== 利用可能なコマンド ========
echo.
echo /speak text:こんにちは voice:voicevox speaker:ずんだもん
echo /voicelist                    - 話者一覧表示
echo /voicevox_status              - 接続状態確認
echo /auto_read enabled:True       - 自動読み上げ設定
echo.

echo ======== 人気の話者 ========
echo.
echo • ずんだもん     - 可愛い東北弁の妖精
echo • 四国めたん     - 関西弁のツンデレ少女
echo • 春日部つむぎ   - 大人っぽいお姉さん
echo • 九州そら       - 九州弁の元気な女の子
echo • WhiteCUL       - クールな歌声ライブラリ
echo.

echo ======== トラブルシューティング ========
echo.
echo Q: ボットが「VOICEVOX not available」と言う
echo A: 1. VOICEVOXアプリを起動
echo    2. 設定でAPIサーバーを有効化
echo    3. /voicevox_status で接続確認
echo.
echo Q: 音声が再生されない
echo A: 1. ボイスチャンネルに参加
echo    2. /join でボットを呼ぶ
echo    3. FFmpegがインストール済みか確認
echo.
echo Q: 特定の話者が選べない
echo A: 1. /voicelist で利用可能話者を確認
echo    2. スペルミスがないかチェック
echo    3. VOICEVOXで該当話者が利用可能か確認
echo.

echo ===============================================
echo.

set /p choice="VOICEVOXダウンロードページを開きますか？ (y/n): "
if /i "%choice%"=="y" (
    echo.
    echo 🌐 ブラウザでVOICEVOX公式サイトを開いています...
    start https://voicevox.hiroshiba.jp/
    echo.
    echo ダウンロード後、上記の手順に従ってセットアップしてください。
) else (
    echo.
    echo 💡 手動でセットアップする場合:
    echo    https://voicevox.hiroshiba.jp/ からダウンロード
)

echo.
echo ===============================================
echo セットアップ完了後、Discord Botを再起動して
echo /voicevox_status コマンドで接続を確認してください！
echo ===============================================
echo.
pause