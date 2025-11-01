"""
RTKS Discord Bot - 設定ファイル例
このファイルを config.py にコピーして使用してください
"""

import os
from dotenv import load_dotenv

# .env ファイルから環境変数を読み込み
load_dotenv()

# ===== Discord Bot 基本設定 =====
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
APPLICATION_ID = os.getenv('APPLICATION_ID', '')

# ===== データベース設定 =====
DB_PATH = os.getenv('DB_PATH', 'bot_database.db')
DB_BACKUP_ENABLED = os.getenv('DB_BACKUP_ENABLED', 'true').lower() == 'true'

# ===== Keep-alive 設定 =====
KEEP_ALIVE_PORT = int(os.getenv('KEEP_ALIVE_PORT', '8080'))
KEEP_ALIVE_ENABLED = os.getenv('KEEP_ALIVE_ENABLED', 'true').lower() == 'true'

# ===== ログ設定 =====
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
LOG_DIR = os.getenv('LOG_DIR', 'logs')

# ===== VOICEVOX 設定 =====
VOICEVOX_URL = os.getenv('VOICEVOX_URL', 'http://localhost:50021')
VOICEVOX_ENABLED = os.getenv('VOICEVOX_ENABLED', 'true').lower() == 'true'

# ===== 経済システム設定 =====
ECONOMY_ENABLED = os.getenv('ECONOMY_ENABLED', 'true').lower() == 'true'
DAILY_REWARD = int(os.getenv('DAILY_REWARD', '1000'))
MINING_REWARD_MIN = int(os.getenv('MINING_REWARD_MIN', '50'))
MINING_REWARD_MAX = int(os.getenv('MINING_REWARD_MAX', '500'))

# ===== 音楽機能設定 =====
MUSIC_ENABLED = os.getenv('MUSIC_ENABLED', 'true').lower() == 'true'
DEFAULT_VOLUME = int(os.getenv('DEFAULT_VOLUME', '50'))

# ===== 開発・デバッグ設定 =====
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
TEST_GUILD_ID = os.getenv('TEST_GUILD_ID', '')

# ===== 詳細設定 =====

# えせ中国語変換設定
CHINESE_CONVERSION = {
    'enabled': True,
    'violation_threshold': 3,  # 違反回数の上限
    'timeout_duration': 300,   # タイムアウト時間（秒）
}

# ロールパネル設定
ROLE_PANEL = {
    'max_roles_per_panel': 25,  # 1つのパネルで設定できる最大ロール数
    'max_panels_per_guild': 10, # サーバーあたりの最大パネル数
}

# 音楽機能の詳細設定
MUSIC_CONFIG = {
    'max_queue_size': 100,      # キューの最大サイズ
    'search_results_limit': 10, # 検索結果の表示数
    'auto_disconnect_timeout': 600, # 自動切断までの時間（秒）
}

# 経済システムの詳細設定
ECONOMY_CONFIG = {
    'starting_balance': 1000,   # 初期残高
    'max_balance': 1000000000,  # 最大残高
    'daily_cooldown': 86400,    # デイリー報酬のクールダウン（秒）
    'mining_cooldown': 3600,    # マイニングのクールダウン（秒）
}

# 自己紹介システム設定
INTRODUCTION_CONFIG = {
    'max_intro_length': 1000,   # 自己紹介の最大文字数
    'auto_delete_timeout': 300, # 自動削除までの時間（秒）
}

# ===== バリデーション =====
def validate_config():
    """設定の妥当性をチェック"""
    errors = []
    
    if not DISCORD_TOKEN:
        errors.append("DISCORD_TOKEN が設定されていません")
    
    if not APPLICATION_ID:
        errors.append("APPLICATION_ID が設定されていません")
    
    if KEEP_ALIVE_PORT < 1 or KEEP_ALIVE_PORT > 65535:
        errors.append("KEEP_ALIVE_PORT は 1-65535 の範囲で設定してください")
    
    if DAILY_REWARD < 0:
        errors.append("DAILY_REWARD は 0 以上で設定してください")
    
    if MINING_REWARD_MIN < 0 or MINING_REWARD_MAX < MINING_REWARD_MIN:
        errors.append("マイニング報酬の設定が不正です")
    
    if DEFAULT_VOLUME < 0 or DEFAULT_VOLUME > 100:
        errors.append("DEFAULT_VOLUME は 0-100 の範囲で設定してください")
    
    if errors:
        print("❌ 設定エラー:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    return True

# 設定の妥当性チェックを実行
if __name__ == "__main__":
    if validate_config():
        print("✅ 設定ファイルは正常です")
    else:
        print("❌ 設定を修正してください")