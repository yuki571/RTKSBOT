# 🤖 RTKS Discord Bot

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3.2+-00ff00.svg)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/your-username/rtks-discord-bot?style=social)](https://github.com/your-username/rtks-discord-bot)
[![GitHub Issues](https://img.shields.io/github/issues/your-username/rtks-discord-bot)](https://github.com/your-username/rtks-discord-bot/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/your-username/rtks-discord-bot)](https://github.com/your-username/rtks-discord-bot/pulls)

**RTKS Discord Bot** は、音楽再生、経済システム、認証機能など多彩な機能を持つ高機能Discordボットです。

## ✨ 主な機能

### 🎵 音楽・音声機能
- **音楽再生**: YouTube、SoundCloudなどからの音楽再生
- **キュー管理**: 再生リスト、シャッフル、ループ機能
- **VOICEVOX連携**: 高品質な日本語音声読み上げ
- **自動読み上げ**: チャンネル別読み上げ設定

### 💰 経済システム
- **デイリー報酬**: 毎日ログインボーナス
- **マイニング**: ランダム報酬獲得
- **ショップ**: アイテム購入システム
- **ランキング**: サーバー内経済ランキング

### 🎭 自己紹介システム
- **自動表示**: ボイスチャンネル参加時に自己紹介表示
- **カスタム設定**: ユーザー別自己紹介登録
- **管理機能**: 管理者による設定管理

### 🔐 認証・管理機能
- **認証パネル**: ボタンクリックによる認証システム
- **ロール管理**: 詳細なロール操作・統計
- **違反管理**: ユーザー違反回数追跡

### 🌐 その他の機能
- **えせ中国語グローバルチャット**: えせ中国語でのサーバー間チャット
- **ログ機能**: 詳細な動作ログ
- **Keep-alive**: クラウドサービス対応

## � プロジェクト構造

```
rtks-discord-bot/
├── 🤖 コアファイル
│   ├── bot.py                 # メインボットファイル
│   ├── database.py            # データベース管理
│   ├── economy.py             # 経済システム
│   └── service_wrapper.py     # サービス管理
├── 🧩 modules/                # 機能別モジュール
│   ├── music.py              # 音楽・VOICEVOX機能
│   ├── auth.py               # 認証・パネル機能
│   ├── roles.py              # ロール管理機能
│   ├── channel_management.py # チャンネル管理機能
│   ├── introduction.py       # 自己紹介システム
│   └── voice.py              # 音声読み上げ機能
├── 📚 docs/                   # ドキュメント
│   ├── 常時稼働ガイド.md
│   ├── 音声読み上げガイド.md
│   └── CONTRIBUTING.md
├── 🔧 scripts/               # セットアップ・実行スクリプト
│   ├── setup.bat
│   ├── start_bot.bat
│   └── setup_voicevox.bat
├── ⚙️ config/                 # 設定テンプレート
│   ├── .env.example
│   └── config.example.py
├── 📦 requirements/           # 依存関係
│   ├── requirements.txt      # 本番用依存関係
│   └── requirements-dev.txt  # 開発用依存関係
├── 💾 data/                   # データベース・バックアップ
├── 📝 logs/                   # ログファイル
├── 🗃️ legacy/                # 古いファイル・バックアップ
└── 📄 設定・ライセンス
    ├── README.md
    ├── setup.py
    └── LICENSE
```

## �🚀 クイックスタート

### 1️⃣ 自動セットアップ（推奨）

#### Windows
```bash
# リポジトリをクローン
git clone https://github.com/your-username/rtks-discord-bot.git
cd rtks-discord-bot

# 自動セットアップ実行
scripts\setup.bat
```

#### Linux/macOS
```bash
# リポジトリをクローン
git clone https://github.com/your-username/rtks-discord-bot.git
cd rtks-discord-bot

# セットアップスクリプトに実行権限付与
chmod +x scripts/setup.sh

# 自動セットアップ実行
scripts/setup.sh
```

### 2️⃣ 設定

1. **Discord Bot Token の取得**
   - [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーション作成
   - Bot タブでトークンを取得

2. **環境変数設定**
   ```bash
   # config/.env.example から .env にコピーして編集
   cp config/.env.example .env
   
   # .env ファイルを編集
   DISCORD_TOKEN=your_discord_bot_token_here
   APPLICATION_ID=your_application_id_here
   ```

3. **設定ファイル調整**
   ```bash
   # config/config.example.py から config.py にコピーして編集
   cp config/config.example.py config.py
   ```

### 3️⃣ 起動

#### Windows
```bash
scripts\start_bot.bat
```

#### Linux/macOS
```bash
scripts/start_bot.sh
```

## 📋 システム要件

### 必須要件
- **Python**: 3.8以上
- **Discord Bot Token**: Discord Developer Portal で取得
- **メモリ**: 最低 512MB RAM
- **ストレージ**: 100MB 以上の空き容量

### オプション要件
- **FFmpeg**: 音楽機能使用時
- **VOICEVOX**: 音声読み上げ機能使用時

## 🎮 使用方法

### 基本コマンド

#### 🎵 音楽コマンド
```
/play <曲名・URL>     - 音楽を再生
/pause               - 一時停止
/resume              - 再生再開
/skip                - スキップ
/queue               - キュー表示
/volume <0-100>      - 音量調整
```

#### 💰 経済コマンド
```
/balance             - 残高確認
/daily               - デイリー報酬
/mine                - マイニング実行
/shop                - ショップ表示
/buy <アイテム>       - アイテム購入
/leaderboard         - ランキング表示
```

#### 🎭 自己紹介コマンド
```
/setup_intro         - システム設定（管理者）
/set_my_intro        - 自己紹介登録
/intro_status        - 設定状況確認
/intro_toggle        - システムON/OFF
```

### 管理者コマンド

#### 🔐 認証・ロール管理
```
/createpanel         - 認証パネル作成
/createrolepanel     - ロールパネル作成
/bulkrole           - 一括ロール操作
/resetviolations    - 違反回数リセット
```

#### ⚙️ 設定コマンド
```
/setlogchannel      - ログチャンネル設定
/setchinesechannel  - えせ中国語チャンネル設定
/setglobalchat      - グローバルチャット設定
```

## 🛠️ 開発・カスタマイズ

### 開発環境セットアップ
```bash
# 開発用依存関係インストール
pip install -r requirements-dev.txt

# コード品質チェック
black .
flake8 .
mypy .

# テスト実行
pytest
```

### ファイル構成
```
rtks-discord-bot/
├── bot.py              # メインボットファイル
├── database.py         # データベース管理
├── economy.py          # 経済システム
├── config.py           # 設定ファイル
├── setup.py            # パッケージ設定
├── requirements.txt    # 依存関係
├── .env.example        # 環境変数例
└── docs/              # ドキュメント
```

### データベース構造
- **SQLite**: 軽量で高速なデータベース
- **12テーブル**: 全機能のデータを管理
- **自動マイグレーション**: アップデート時自動対応
- **バックアップ機能**: データ保護システム

## 🔧 トラブルシューティング

### よくある問題

#### 1. FFmpeg エラー
```bash
# Windows (Chocolatey)
choco install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# macOS (Homebrew)
brew install ffmpeg
```

#### 2. VOICEVOX 接続エラー
- VOICEVOX エンジンが起動しているか確認
- ポート50021が開いているか確認
- `config.py` の `VOICEVOX_URL` 設定を確認

#### 3. データベースエラー
```bash
# データベース確認
python -c "from database import db_manager; db_manager.verify_tables()"

# バックアップから復元
cp bot_database_backup_*.db bot_database.db
```

#### 4. 権限エラー
- Botに必要な権限が付与されているか確認
- 管理者権限、メッセージ送信権限など

### ログ確認
```bash
# ログファイル確認
tail -f bot_log_$(date +%Y%m%d).log

# リアルタイムログ
python bot.py  # コンソール出力を確認
```

## 🤝 コントリビューション

1. リポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/new-feature`)
3. 変更をコミット (`git commit -am 'Add new feature'`)
4. ブランチにプッシュ (`git push origin feature/new-feature`)
5. プルリクエストを作成

詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご確認ください。

## 📜 ライセンス

このプロジェクトは [MIT License](LICENSE) の下で公開されています。

## 📞 サポート

- **Issues**: [GitHub Issues](https://github.com/your-username/rtks-discord-bot/issues)
- **Discord**: [サポートサーバー](https://discord.gg/your-invite)
- **Wiki**: [プロジェクトWiki](https://github.com/your-username/rtks-discord-bot/wiki)

## 🙏 謝辞

- [discord.py](https://github.com/Rapptz/discord.py) - Discordボットライブラリ
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 動画ダウンロードライブラリ
- [VOICEVOX](https://voicevox.hiroshiba.jp/) - 音声合成エンジン

---

⭐ このプロジェクトが役に立った場合は、スターを付けてください！
