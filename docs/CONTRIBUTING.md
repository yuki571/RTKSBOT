# 🤝 Contributing to RTKS Discord Bot

このプロジェクトにコントリビュートしていただき、ありがとうございます！

## 📋 コントリビューションガイドライン

### 🚀 開発環境のセットアップ

1. **リポジトリのフォーク・クローン**
   ```bash
   # フォークしたリポジトリをクローン
   git clone https://github.com/your-username/rtks-discord-bot.git
   cd rtks-discord-bot
   
   # オリジナルリポジトリをアップストリームに追加
   git remote add upstream https://github.com/original-username/rtks-discord-bot.git
   ```

2. **開発環境セットアップ**
   ```bash
   # 開発用セットアップスクリプト実行
   ./setup.sh  # Linux/macOS
   setup.bat   # Windows
   
   # 開発用依存関係インストール
   pip install -r requirements-dev.txt
   
   # Pre-commit フック設定
   pre-commit install
   ```

3. **テスト用Discord Bot設定**
   ```bash
   # テスト用の .env ファイル作成
   cp .env.example .env.test
   # TEST_GUILD_ID にテストサーバーのIDを設定
   ```

### 🔧 開発ワークフロー

1. **新機能開発・バグ修正**
   ```bash
   # 最新のmainブランチを取得
   git checkout main
   git pull upstream main
   
   # 新しいブランチ作成
   git checkout -b feature/your-feature-name
   # または
   git checkout -b fix/bug-description
   ```

2. **コード品質チェック**
   ```bash
   # コードフォーマット
   black .
   isort .
   
   # リンター実行
   flake8 .
   mypy .
   
   # テスト実行
   pytest
   pytest --cov=. --cov-report=html  # カバレッジ付き
   ```

3. **コミット・プッシュ**
   ```bash
   # 変更をステージング
   git add .
   
   # コミット（コミットメッセージ規約に従う）
   git commit -m "feat: add new economy system feature"
   
   # プッシュ
   git push origin feature/your-feature-name
   ```

### 📝 コミットメッセージ規約

[Conventional Commits](https://www.conventionalcommits.org/) を使用します：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Type一覧
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント変更
- `style`: コード動作に影響しない変更（フォーマット等）
- `refactor`: リファクタリング
- `perf`: パフォーマンス改善
- `test`: テスト追加・修正
- `chore`: ビルドプロセス・補助ツール変更

#### 例
```
feat(economy): add mining system with cooldown
fix(music): resolve queue skip issue
docs: update installation guide
style: format code with black
refactor(database): optimize query performance
test(auth): add unit tests for role panel
```

### 🧪 テストガイドライン

#### テストの種類
- **単体テスト**: 個別機能のテスト
- **統合テスト**: モジュール間の連携テスト
- **E2Eテスト**: Discord Bot全体の動作テスト

#### テストファイル構成
```
tests/
├── unit/
│   ├── test_database.py
│   ├── test_economy.py
│   └── test_auth.py
├── integration/
│   ├── test_bot_commands.py
│   └── test_voice_features.py
└── fixtures/
    ├── mock_discord.py
    └── test_data.json
```

#### テスト実行
```bash
# 全テスト実行
pytest

# 特定のテストファイル
pytest tests/unit/test_economy.py

# 特定のテスト関数
pytest tests/unit/test_economy.py::test_daily_reward

# カバレッジ付きテスト
pytest --cov=. --cov-report=html
```

### 📚 コーディング規約

#### Python コーディングスタイル
- **PEP 8** に準拠
- **Black** でコードフォーマット
- **isort** でインポート整理
- **mypy** で型チェック

#### 命名規約
```python
# 変数・関数: snake_case
user_balance = 1000
def get_user_data():
    pass

# クラス: PascalCase
class EconomySystem:
    pass

# 定数: UPPER_SNAKE_CASE
MAX_BALANCE = 1000000

# プライベート: アンダースコア接頭辞
def _internal_function():
    pass
```

#### ドキュメンテーション
```python
def calculate_mining_reward(user_id: int, difficulty: float) -> int:
    """マイニング報酬を計算する
    
    Args:
        user_id: ユーザーID
        difficulty: マイニング難易度（0.0-1.0）
    
    Returns:
        計算された報酬額
    
    Raises:
        ValueError: 難易度が範囲外の場合
    """
    pass
```

### 🐛 バグレポート

GitHub Issues でバグレポートを作成する際は以下を含めてください：

#### バグレポートテンプレート
```
## 🐛 バグ報告

### 期待される動作
何が起こるべきだったかを説明

### 実際の動作
実際に何が起こったかを説明

### 再現手順
1. '...'へ移動
2. '....'をクリック
3. '....'まで下にスクロール
4. エラーを確認

### 環境情報
- OS: [例：Windows 11]
- Python バージョン: [例：3.11.0]
- Bot バージョン: [例：1.2.0]
- discord.py バージョン: [例：2.3.2]

### 追加情報
スクリーンショット、ログファイル、その他関連情報
```

### ✨ 機能リクエスト

新機能の提案は GitHub Issues で以下のテンプレートを使用：

```
## 💡 機能リクエスト

### 問題の説明
現在の状況で困っていることを説明

### 提案する解決策
どのような機能があれば解決するかを説明

### 代替案
他に考えられる解決策があれば説明

### 追加情報
参考資料、類似機能を持つ他のBotなど
```

### 📖 ドキュメント改善

ドキュメントの改善も歓迎します：

- README.md の更新
- コードコメントの改善
- Wiki ページの作成
- 使用方法ガイドの追加

### 🎯 プルリクエストガイドライン

#### プルリクエスト作成前チェックリスト
- [ ] 関連する Issue が存在する
- [ ] コードがフォーマットされている（black, isort実行済み）
- [ ] リンターチェックをパスしている（flake8, mypy）
- [ ] テストが通っている（pytest実行済み）
- [ ] 新機能にはテストが追加されている
- [ ] ドキュメントが更新されている（必要に応じて）

#### プルリクエストテンプレート
```
## 📝 変更内容

### 変更の種類
- [ ] バグ修正
- [ ] 新機能
- [ ] リファクタリング
- [ ] ドキュメント更新
- [ ] その他

### 説明
この変更で何が改善されるかを説明

### 関連Issue
Closes #123

### テスト
- [ ] 既存のテストが通る
- [ ] 新しいテストを追加した
- [ ] 手動でテストした

### チェックリスト
- [ ] コードレビューを依頼した
- [ ] ドキュメントを更新した
- [ ] Breaking changeがある場合は明記した
```

### 🤝 コミュニティ行動規約

- 建設的で敬意のあるコミュニケーション
- 多様性を尊重し、包括的な環境作り
- 学習と成長を支援する姿勢
- オープンソースプロジェクトの精神を大切に

### 📞 サポート・質問

- **GitHub Discussions**: 一般的な質問・議論
- **GitHub Issues**: バグレポート・機能リクエスト
- **Discord サーバー**: リアルタイムサポート

### 🙏 謝辞

すべてのコントリビューターに感謝します！あなたの貢献がこのプロジェクトをより良いものにしています。

---

Happy Coding! 🚀