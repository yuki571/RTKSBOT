import sqlite3
import os
import json
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_path=None, workspace_root=None):
        workspace_root = workspace_root or os.getcwd()
        self.folder = os.path.join(workspace_root, 'DETABASE')
        os.makedirs(self.folder, exist_ok=True)
        self.db_path = db_path or os.path.join(self.folder, 'data.db')
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self):
        c = self.conn.cursor()
        # messages: store each message timestamp for counts/pruning
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
        ''')
        # violations: per-user per-guild
        c.execute('''
            CREATE TABLE IF NOT EXISTS violations (
                user_key TEXT PRIMARY KEY,
                count INTEGER DEFAULT 0,
                has_role INTEGER DEFAULT 0
            );
        ''')
        # guild_settings: store JSON blob for each guild
        c.execute('''
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id TEXT PRIMARY KEY,
                settings TEXT
            );
        ''')
        # kv: generic key/value storage
        c.execute('''
            CREATE TABLE IF NOT EXISTS kv (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        ''')
        self.conn.commit()

    # Messages operations
    def add_message(self, guild_id: str, channel_id: str, timestamp_iso: str):
        c = self.conn.cursor()
        c.execute("INSERT INTO messages (guild_id, channel_id, timestamp) VALUES (?, ?, ?)", (guild_id, channel_id, timestamp_iso))
        self.conn.commit()

    def count_messages_in_period(self, guild_id: str, channel_id: str, days: int) -> int:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM messages WHERE guild_id = ? AND channel_id = ? AND timestamp >= ?", (guild_id, channel_id, cutoff))
        row = c.fetchone()
        return row['cnt'] if row else 0

    def count_messages_in_range(self, guild_id: str, channel_id: str, start_iso: str, end_iso: str) -> int:
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM messages WHERE guild_id = ? AND channel_id = ? AND timestamp >= ? AND timestamp <= ?", (guild_id, channel_id, start_iso, end_iso))
        row = c.fetchone()
        return row['cnt'] if row else 0

    def prune_old(self, days: int, guild_id: str | None = None):
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self.conn.cursor()
        if guild_id:
            c.execute("DELETE FROM messages WHERE guild_id = ? AND timestamp < ?", (guild_id, cutoff))
        else:
            c.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff,))
        self.conn.commit()

    # violations
    def load_violations(self) -> dict:
        c = self.conn.cursor()
        c.execute("SELECT user_key, count, has_role FROM violations")
        rows = c.fetchall()
        return {r['user_key']: {'count': r['count'], 'has_role': bool(r['has_role'])} for r in rows}

    def add_violation(self, user_id: str, guild_id: str) -> bool:
        user_key = f"{user_id}_{guild_id}"
        c = self.conn.cursor()
        c.execute("SELECT count FROM violations WHERE user_key = ?", (user_key,))
        row = c.fetchone()
        if row:
            new_count = row['count'] + 1
            c.execute("UPDATE violations SET count = ? WHERE user_key = ?", (new_count, user_key))
        else:
            new_count = 1
            c.execute("INSERT INTO violations (user_key, count, has_role) VALUES (?, ?, 0)", (user_key, new_count))
        self.conn.commit()
        return new_count >= 10

    def set_illegal_role_flag(self, user_id: str, guild_id: str):
        user_key = f"{user_id}_{guild_id}"
        c = self.conn.cursor()
        c.execute("UPDATE violations SET has_role = 1 WHERE user_key = ?", (user_key,))
        self.conn.commit()

    def has_illegal_role(self, user_id: str, guild_id: str) -> bool:
        user_key = f"{user_id}_{guild_id}"
        c = self.conn.cursor()
        c.execute("SELECT has_role FROM violations WHERE user_key = ?", (user_key,))
        row = c.fetchone()
        return bool(row['has_role']) if row else False

    # guild settings
    def load_guild_settings(self, guild_id: str) -> dict:
        c = self.conn.cursor()
        c.execute("SELECT settings FROM guild_settings WHERE guild_id = ?", (str(guild_id),))
        row = c.fetchone()
        if row and row['settings']:
            try:
                return json.loads(row['settings'])
            except Exception:
                return {}
        return {}

    def save_guild_settings(self, guild_id: str, settings: dict):
        j = json.dumps(settings, ensure_ascii=False)
        c = self.conn.cursor()
        c.execute("INSERT INTO guild_settings (guild_id, settings) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET settings = excluded.settings", (str(guild_id), j))
        self.conn.commit()

    # kv store
    def set_kv(self, key: str, value):
        j = json.dumps(value, ensure_ascii=False)
        c = self.conn.cursor()
        c.execute("INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, j))
        self.conn.commit()

    def get_kv(self, key: str, default=None):
        c = self.conn.cursor()
        c.execute("SELECT value FROM kv WHERE key = ?", (key,))
        row = c.fetchone()
        if not row:
            return default
        try:
            return json.loads(row['value'])
        except Exception:
            return row['value']

    # migration helpers
    def migrate_kaso_data(self, kaso_file):
        if not os.path.exists(kaso_file):
            return
        with open(kaso_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        c = self.conn.cursor()
        for guild_id, g in data.items():
            for ch_id, timestamps in g.items():
                for ts in timestamps:
                    c.execute("INSERT INTO messages (guild_id, channel_id, timestamp) VALUES (?, ?, ?)", (guild_id, ch_id, ts))
        self.conn.commit()

    def migrate_guild_settings(self, settings_folder):
        if not os.path.isdir(settings_folder):
            return
        for name in os.listdir(settings_folder):
            path = os.path.join(settings_folder, name)
            if name.endswith('.json'):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                guild_id = name.replace('guild_settings_', '').replace('.json','')
                self.save_guild_settings(guild_id, data)

    def migrate_violations(self, violations_file):
        if not os.path.exists(violations_file):
            return
        with open(violations_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        c = self.conn.cursor()
        for k, v in data.items():
            count = v.get('count', 0)
            has_role = int(v.get('has_role', False))
            c.execute("INSERT OR REPLACE INTO violations (user_key, count, has_role) VALUES (?, ?, ?)", (k, count, has_role))
        self.conn.commit()

    def migrate_all(self, workspace_root=None):
        root = workspace_root or os.getcwd()
        # migrate known files
        kaso_file = os.path.join(root, 'kaso_data.json')
        self.migrate_kaso_data(kaso_file)
        violations_file = os.path.join(root, 'violations.json')
        self.migrate_violations(violations_file)
        settings_folder = os.path.join(root, 'guild_settings')
        self.migrate_guild_settings(settings_folder)
        # migrate arbitrary json files into kv
        for fname in ['allowed_users.json', 'super_users.json', 'global_chat_settings.json', 'chinese_channels.json']:
            path = os.path.join(root, fname)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    try:
                        j = json.load(f)
                        self.set_kv(fname, j)
                    except Exception:
                        pass

    def close(self):
        self.conn.close()
