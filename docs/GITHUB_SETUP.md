# 🚀 GitHub公開セットアップガイド

このガイドでは、RTKS Discord BotをGitHubに公開する手順を詳しく説明します。

## 📋 事前準備

### 1. GitHubアカウント作成
- [GitHub](https://github.com)でアカウントを作成（未作成の場合）
- メールアドレスの認証を完了

### 2. 機密情報の確認
以下のファイルが`.gitignore`で除外されていることを確認：
- `config.py` (実際の設定ファイル)
- `.env` (環境変数ファイル)
- `data/` (データベースファイル)
- `logs/` (ログファイル)
- `legacy/` (バックアップファイル)

## 🛠️ ローカルGit設定

### 1. Gitの初期化
```bash
# プロジェクトディレクトリで実行
git init
git add .
git commit -m "🎉 Initial commit: RTKS Discord Bot v2.0.0

✨ Features:
- Modular architecture with 6 feature modules
- Music playback with VOICEVOX integration
- Economy system with daily rewards
- Authentication and role management
- Channel management and global chat
- Introduction system for voice channels

🏗️ Structure:
- Clean folder organization
- Separated documentation, scripts, and config
- Professional project layout for open source
"
```

### 2. Git設定（初回のみ）
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## 🌐 GitHubリポジトリ作成

### 方法1: GitHub Web Interface（推奨）

1. **GitHub.comでリポジトリ作成**
   - [GitHub](https://github.com)にログイン
   - 右上の「+」→「New repository」
   - Repository name: `rtks-discord-bot`
   - Description: `🤖 高機能日本語Discordボット - 音楽再生、経済システム、認証機能搭載`
   - Public/Private を選択
   - 「Create repository」をクリック

2. **ローカルとリモートを接続**
```bash
git remote add origin https://github.com/your-username/rtks-discord-bot.git
git branch -M main
git push -u origin main
```

### 方法2: GitHub CLI（上級者向け）

```bash
# GitHub CLIをインストール後
gh repo create rtks-discord-bot --public --description "🤖 高機能日本語Discordボット - 音楽再生、経済システム、認証機能搭載"
git remote add origin https://github.com/your-username/rtks-discord-bot.git
git push -u origin main
```

## 📝 リポジトリ設定の最適化

### 1. Aboutセクション設定
- GitHub リポジトリページの「About」を編集
- Website: (ボットの招待リンクやドキュメントサイト)
- Topics: `discord-bot`, `python`, `music-bot`, `japanese`, `voicevox`, `economy-bot`

### 2. ブランチ保護設定（オプション）
- Settings → Branches
- main ブランチの保護ルール設定
- Pull Request 必須化

### 3. Issues と Projects 有効化
- Settings → Features
- Issues, Wiki, Projects を有効化

## 🏷️ リリース作成

### 1. 初回リリース
```bash
git tag -a v2.0.0 -m "🎉 Initial Release v2.0.0

🚀 新機能:
- モジュラーアーキテクチャ
- 音楽再生システム
- 経済システム
- 認証・ロール管理
- VOICEVOX連携

🏗️ プロジェクト構造:
- 6つの機能別モジュール
- 整理されたフォルダ構造
- 包括的なドキュメント
"

git push origin v2.0.0
```

### 2. GitHubでリリース作成
- Releases → Create a new release
- Tag: v2.0.0
- Release title: `🎉 RTKS Discord Bot v2.0.0 - Initial Release`
- 詳細な変更履歴を記載

## 🤝 コントリビューション設定

### 1. Issue テンプレート作成
```bash
mkdir -p .github/ISSUE_TEMPLATE
```

### 2. Pull Request テンプレート作成
```bash
mkdir -p .github
```

### 3. Code of Conduct 追加
- GitHub の Code of Conduct Generator を使用

## 📊 プロジェクト管理

### 1. GitHub Actions 設定（オプション）
- 自動テスト
- コード品質チェック
- 自動デプロイ

### 2. Wiki 設定
- 詳細なセットアップガイド
- API ドキュメント
- FAQ

## 🔗 有用なリンク

- [GitHub Docs](https://docs.github.com/)
- [Git チートシート](https://training.github.com/downloads/ja/github-git-cheat-sheet/)
- [Markdown ガイド](https://guides.github.com/features/mastering-markdown/)

## ⚠️ 注意事項

1. **機密情報の確認**: Botトークンや設定ファイルがpushされていないか必ず確認
2. **ライセンス選択**: 適切なライセンス（MIT, Apache, etc.）を選択
3. **定期更新**: READMEとドキュメントを定期的に更新
4. **セキュリティ**: Dependabot でセキュリティアップデートを有効化

---

💡 **ヒント**: 初回公開後は、定期的なコミットと明確なコミットメッセージでプロジェクトの成長を記録しましょう！