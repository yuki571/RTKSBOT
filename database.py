# Discord Bot Database Manager
import sqlite3
import json
import os
import asyncio
import aiosqlite
from datetime import datetime
import logging

# ログ設定
db_logger = logging.getLogger('database')

class DatabaseManager:
    def __init__(self, db_path="bot_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """データベース初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # ギルド設定テーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS guild_settings (
                        guild_id INTEGER PRIMARY KEY,
                        chinese_channels TEXT,
                        global_chat_channel_id INTEGER,
                        voice_mode BOOLEAN DEFAULT 1,
                        music_mode BOOLEAN DEFAULT 0,
                        auto_read_channel_id INTEGER,
                        auto_read_voice TEXT DEFAULT 'voicevox',
                        auto_read_speaker TEXT DEFAULT 'ずんだもん',
                        auto_read_max_length INTEGER DEFAULT 100,
                        log_channel_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # ユーザー音声設定テーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_voice_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        user_id INTEGER,
                        speaker TEXT,
                        emotion TEXT DEFAULT 'normal',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(guild_id, user_id)
                    )
                ''')
                
                # 経済システム - ユーザー残高テーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_economy (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        user_id INTEGER,
                        balance INTEGER DEFAULT 1000,
                        total_earned INTEGER DEFAULT 1000,
                        total_spent INTEGER DEFAULT 0,
                        last_daily TIMESTAMP,
                        mining_power INTEGER DEFAULT 1,
                        mining_auto BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(guild_id, user_id)
                    )
                ''')
                
                # 経済システム - トランザクション履歴
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS economy_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        user_id INTEGER,
                        transaction_type TEXT,
                        amount INTEGER,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 経済システム - ショップアイテム
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS shop_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        item_name TEXT,
                        item_description TEXT,
                        price INTEGER,
                        item_type TEXT,
                        effect_value INTEGER,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 経済システム - ユーザーアイテム所有
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        user_id INTEGER,
                        item_id INTEGER,
                        quantity INTEGER DEFAULT 1,
                        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (item_id) REFERENCES shop_items (id)
                    )
                ''')
                
                # マイニング履歴
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mining_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        user_id INTEGER,
                        amount INTEGER,
                        mining_power INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 許可ユーザーテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS allowed_users (
                        user_id INTEGER PRIMARY KEY,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # スーパーユーザーテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS super_users (
                        user_id INTEGER PRIMARY KEY,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 違反記録テーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_violations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        user_id INTEGER,
                        violation_count INTEGER DEFAULT 0,
                        has_role BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(guild_id, user_id)
                    )
                ''')
                
                # 自己紹介システムテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_introductions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER,
                        user_id INTEGER,
                        introduction_text TEXT,
                        intro_channel_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(guild_id, user_id)
                    )
                ''')
                
                # 自己紹介システム設定テーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS intro_settings (
                        guild_id INTEGER PRIMARY KEY,
                        intro_channel_id INTEGER,
                        secret_role_name TEXT DEFAULT "秘密のロール",
                        is_enabled BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                db_logger.info("Database initialized successfully")
                
        except Exception as e:
            db_logger.error(f"Database initialization error: {e}")
    
    def backup_database(self):
        """データベースをバックアップ"""
        try:
            if os.path.exists(self.db_path):
                backup_name = f"bot_database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                import shutil
                shutil.copy2(self.db_path, backup_name)
                db_logger.info(f"Database backed up to: {backup_name}")
                
                # 古いバックアップファイルを削除（10個まで保持）
                import glob
                backup_files = sorted(glob.glob("bot_database_backup_*.db"))
                if len(backup_files) > 10:
                    for old_backup in backup_files[:-10]:
                        os.remove(old_backup)
                        db_logger.info(f"Removed old backup: {old_backup}")
        except Exception as e:
            db_logger.error(f"Backup error: {e}")
    
    async def migrate_from_json(self):
        """既存のJSONファイルからDBに移行"""
        try:
            # 移行前にバックアップ作成
            self.backup_database()
            
            async with aiosqlite.connect(self.db_path) as db:
                # 1. ギルド設定の移行
                await self._migrate_guild_settings(db)
                
                # 2. 許可ユーザーの移行
                await self._migrate_allowed_users(db)
                
                # 3. スーパーユーザーの移行
                await self._migrate_super_users(db)
                
                # 4. 違反記録の移行
                await self._migrate_violations(db)
                
                await db.commit()
                
                # 移行完了フラグを作成
                with open('.migration_completed', 'w') as f:
                    f.write(f"Migration completed at {datetime.now()}")
                
                db_logger.info("Complete JSON to DB migration finished")
                
        except Exception as e:
            db_logger.error(f"Migration error: {e}")
    
    async def _migrate_guild_settings(self, db):
        """ギルド設定ファイルの移行"""
        # guild_settingsフォルダ内のJSONファイル
        guild_folder = 'guild_settings'
        all_guild_files = []
        
        if os.path.exists(guild_folder):
            guild_files = [f for f in os.listdir(guild_folder) if f.startswith('guild_settings_') and f.endswith('.json')]
            for file in guild_files:
                all_guild_files.append(os.path.join(guild_folder, file))
        
        # 旧形式のギルド設定ファイル（ルートディレクトリ）
        root_guild_files = [f for f in os.listdir('.') if f.startswith('guild_settings_') and f.endswith('.json')]
        for file in root_guild_files:
            all_guild_files.append(file)
        
        for file_path in all_guild_files:
            try:
                # ファイル名からguild_idを抽出
                filename = os.path.basename(file_path)
                guild_id = int(filename.replace('guild_settings_', '').replace('.json', ''))
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # ギルド設定を挿入
                await db.execute('''
                    INSERT OR REPLACE INTO guild_settings (
                        guild_id, chinese_channels, global_chat_channel_id, 
                        voice_mode, music_mode, auto_read_channel_id,
                        auto_read_voice, auto_read_speaker, auto_read_max_length
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    guild_id,
                    json.dumps(data.get('chinese_channels', [])),
                    data.get('global_chat_channel_id'),
                    data.get('voice_mode', True),
                    data.get('music_mode', False),
                    data.get('auto_read', {}).get('channel_id'),
                    data.get('auto_read', {}).get('voice', 'voicevox'),
                    data.get('auto_read', {}).get('speaker', 'ずんだもん'),
                    data.get('auto_read', {}).get('max_length', 100)
                ))
                
                # ユーザー音声設定を移行
                user_voices = data.get('user_voices', {})
                for user_id, voice_data in user_voices.items():
                    await db.execute('''
                        INSERT OR REPLACE INTO user_voice_settings (
                            guild_id, user_id, speaker, emotion
                        ) VALUES (?, ?, ?, ?)
                    ''', (
                        guild_id,
                        int(user_id),
                        voice_data.get('speaker', 'ずんだもん'),
                        voice_data.get('emotion', 'normal')
                    ))
                
                db_logger.info(f"Migrated guild settings: {guild_id} from {file_path}")
                
            except Exception as e:
                db_logger.error(f"Error migrating {file_path}: {e}")
    
    async def _migrate_allowed_users(self, db):
        """許可ユーザーファイルの移行"""
        if os.path.exists('allowed_users.json'):
            try:
                with open('allowed_users.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for user_id in data.get('allowed_users', []):
                    await db.execute('''
                        INSERT OR IGNORE INTO allowed_users (user_id) VALUES (?)
                    ''', (user_id,))
                
                db_logger.info(f"Migrated {len(data.get('allowed_users', []))} allowed users")
                
            except Exception as e:
                db_logger.error(f"Error migrating allowed_users.json: {e}")
    
    async def _migrate_super_users(self, db):
        """スーパーユーザーファイルの移行"""
        if os.path.exists('super_users.json'):
            try:
                with open('super_users.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for user_id in data.get('super_users', []):
                    await db.execute('''
                        INSERT OR IGNORE INTO super_users (user_id) VALUES (?)
                    ''', (user_id,))
                
                db_logger.info(f"Migrated {len(data.get('super_users', []))} super users")
                
            except Exception as e:
                db_logger.error(f"Error migrating super_users.json: {e}")
    
    async def _migrate_violations(self, db):
        """違反記録ファイルの移行"""
        if os.path.exists('violations.json'):
            try:
                with open('violations.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for user_guild_key, violation_data in data.items():
                    # キーの形式: "user_id_guild_id"
                    parts = user_guild_key.split('_')
                    if len(parts) >= 2:
                        user_id = int(parts[0])
                        guild_id = int(parts[1])
                        
                        await db.execute('''
                            INSERT OR REPLACE INTO user_violations (
                                guild_id, user_id, violation_count, has_role
                            ) VALUES (?, ?, ?, ?)
                        ''', (
                            guild_id,
                            user_id,
                            violation_data.get('count', 0),
                            violation_data.get('has_role', False)
                        ))
                
                db_logger.info(f"Migrated {len(data)} violation records")
                
            except Exception as e:
                db_logger.error(f"Error migrating violations.json: {e}")
    
    def is_migration_needed(self):
        """移行が必要かチェック"""
        # 移行完了フラグが存在しない かつ JSONファイルが存在する場合のみ移行
        migration_completed = os.path.exists('.migration_completed')
        
        # 移行対象のJSONファイルをチェック
        json_files_exist = (
            os.path.exists('allowed_users.json') or
            os.path.exists('super_users.json') or
            os.path.exists('violations.json') or
            any(f.startswith('guild_settings_') and f.endswith('.json') for f in os.listdir('.')) or
            (os.path.exists('guild_settings') and 
             any(f.startswith('guild_settings_') and f.endswith('.json') for f in os.listdir('guild_settings')))
        )
        
        return not migration_completed and json_files_exist
    
    async def setup_default_shop_items(self, guild_id):
        """デフォルトショップアイテムをセットアップ"""
        default_items = [
            ("💻 普通のPC", "基本的なマイニング機器", 5000, "mining_power", 2),
            ("🖥️ ゲーミングPC", "高性能マイニング機器", 15000, "mining_power", 5),
            ("⛏️ ASIC マイナー", "専用マイニング機器", 50000, "mining_power", 15),
            ("🏭 マイニングファーム", "自動マイニング施設", 100000, "mining_auto", 1),
            ("🚀 量子コンピューター", "最強のマイニングマシン", 500000, "mining_power", 100),
            ("💎 ダイヤモンドハンド", "HODLで追加ボーナス", 25000, "daily_bonus", 500),
            ("📈 投資の神", "毎日のボーナス2倍", 75000, "daily_multiplier", 2),
            ("🎰 ラッキーチャーム", "ギャンブル成功率アップ", 10000, "luck_boost", 20),
        ]
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                for item_name, description, price, item_type, effect_value in default_items:
                    await db.execute('''
                        INSERT OR IGNORE INTO shop_items (
                            guild_id, item_name, item_description, price, item_type, effect_value
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (guild_id, item_name, description, price, item_type, effect_value))
                
                await db.commit()
                db_logger.info(f"Default shop items setup for guild {guild_id}")
                
        except Exception as e:
            db_logger.error(f"Error setting up shop items: {e}")

# グローバルインスタンス
db_manager = DatabaseManager()