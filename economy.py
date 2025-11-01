# Discord Bot Economy System with PC Parts Mining
import discord
from discord import app_commands
import asyncio
import aiosqlite
import random
import json
from datetime import datetime, timedelta
import logging
from database import db_manager
from modules.pc_parts import PCPartsData

# ログ設定
economy_logger = logging.getLogger('economy')

class EconomySystem:
    def __init__(self):
        self.currency_name = "RTKS Coin"
        self.currency_symbol = "🪙"
        self.daily_base_amount = 1000
        self.mining_base_reward = 50
        
    async def get_user_balance(self, guild_id, user_id):
        """ユーザーの残高を取得"""
        try:
            async with aiosqlite.connect(db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT balance FROM user_economy 
                    WHERE guild_id = ? AND user_id = ?
                ''', (guild_id, user_id))
                result = await cursor.fetchone()
                
                if result:
                    return result[0]
                else:
                    # 新規ユーザーの場合、初期残高で作成
                    await db.execute('''
                        INSERT INTO user_economy (guild_id, user_id, balance, total_earned)
                        VALUES (?, ?, ?, ?)
                    ''', (guild_id, user_id, 1000, 1000))
                    await db.commit()
                    return 1000
                    
        except Exception as e:
            economy_logger.error(f"Error getting user balance: {e}")
            return 0
    
    async def update_balance(self, guild_id, user_id, amount, transaction_type, description):
        """残高を更新してトランザクション記録"""
        try:
            async with aiosqlite.connect(db_manager.db_path) as db:
                # 現在の残高を取得
                current_balance = await self.get_user_balance(guild_id, user_id)
                new_balance = current_balance + amount
                
                if new_balance < 0:
                    return False, "残高不足です"
                
                # 残高更新
                await db.execute('''
                    UPDATE user_economy 
                    SET balance = ?, 
                        total_earned = total_earned + ?,
                        total_spent = total_spent + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE guild_id = ? AND user_id = ?
                ''', (new_balance, max(0, amount), max(0, -amount), guild_id, user_id))
                
                # トランザクション記録
                await db.execute('''
                    INSERT INTO economy_transactions (
                        guild_id, user_id, transaction_type, amount, description
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (guild_id, user_id, transaction_type, amount, description))
                
                await db.commit()
                return True, new_balance
                
        except Exception as e:
            economy_logger.error(f"Error updating balance: {e}")
            return False, str(e)
    
    async def daily_reward(self, guild_id, user_id):
        """デイリー報酬"""
        try:
            async with aiosqlite.connect(db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT last_daily FROM user_economy 
                    WHERE guild_id = ? AND user_id = ?
                ''', (guild_id, user_id))
                result = await cursor.fetchone()
                
                if result and result[0]:
                    last_daily = datetime.fromisoformat(result[0])
                    if datetime.now() - last_daily < timedelta(hours=20):  # 20時間クールダウン
                        remaining = timedelta(hours=20) - (datetime.now() - last_daily)
                        hours = remaining.seconds // 3600
                        minutes = (remaining.seconds % 3600) // 60
                        return False, f"次のデイリー報酬まで {hours}時間{minutes}分"
                
                # ランダムボーナス
                base_amount = self.daily_base_amount
                bonus_multiplier = random.uniform(1.0, 2.5)
                final_amount = int(base_amount * bonus_multiplier)
                
                # 残高更新
                success, new_balance = await self.update_balance(
                    guild_id, user_id, final_amount, "daily", f"デイリー報酬 (x{bonus_multiplier:.2f})"
                )
                
                if success:
                    # last_daily更新
                    await db.execute('''
                        UPDATE user_economy 
                        SET last_daily = CURRENT_TIMESTAMP 
                        WHERE guild_id = ? AND user_id = ?
                    ''', (guild_id, user_id))
                    await db.commit()
                    
                    return True, {
                        'amount': final_amount,
                        'multiplier': bonus_multiplier,
                        'new_balance': new_balance
                    }
                
                return False, "エラーが発生しました"
                
        except Exception as e:
            economy_logger.error(f"Error in daily reward: {e}")
            return False, str(e)
    
    async def mining_reward(self, guild_id, user_id):
        """PCパーツベースマイニング報酬"""
        try:
            async with aiosqlite.connect(db_manager.db_path) as db:
                # ユーザーのPC構成を取得
                cursor = await db.execute('''
                    SELECT pc_parts, mining_power FROM user_economy 
                    WHERE guild_id = ? AND user_id = ?
                ''', (guild_id, user_id))
                result = await cursor.fetchone()
                
                if result and result[0]:
                    # PC構成が存在する場合
                    try:
                        user_parts = json.loads(result[0])
                        
                        # PC構成の有効性チェック
                        is_valid, message = PCPartsData.is_build_valid(user_parts)
                        if not is_valid:
                            return False, f"PC構成エラー: {message}"
                        
                        # ハッシュレート計算
                        total_hash_rate = PCPartsData.calculate_total_hash_rate(user_parts)
                        power_consumption = PCPartsData.calculate_power_consumption(user_parts)
                        
                        # マイニング効率計算（消費電力も考慮）
                        efficiency = total_hash_rate / max(power_consumption, 1) if power_consumption > 0 else total_hash_rate
                        
                    except json.JSONDecodeError:
                        # JSONパース失敗時は従来のmining_powerを使用
                        total_hash_rate = result[1] if result[1] else 1
                        efficiency = 1.0
                        power_consumption = 100
                else:
                    # PC構成がない場合はデフォルト
                    total_hash_rate = 1
                    efficiency = 1.0
                    power_consumption = 100
                
                # マイニング報酬計算
                base_reward = int(self.mining_base_reward * total_hash_rate)
                
                # 効率ボーナス
                efficiency_bonus = min(efficiency * 0.1, 0.5)  # 最大50%ボーナス
                
                # ランダム要素
                variance = random.uniform(0.8, 1.2)
                
                # 電力コスト（高消費電力は報酬減少）
                power_penalty = max(0.5, 1.0 - (power_consumption - 200) / 2000)
                
                final_reward = int(base_reward * (1 + efficiency_bonus) * variance * power_penalty)
                
                # 残高更新
                success, new_balance = await self.update_balance(
                    guild_id, user_id, final_reward, "mining", 
                    f"PCマイニング報酬 (ハッシュレート: {total_hash_rate} MH/s)"
                )
                
                if success:
                    # マイニング履歴記録
                    await db.execute('''
                        INSERT INTO mining_history (guild_id, user_id, amount, mining_power, hash_rate, power_consumption)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (guild_id, user_id, final_reward, total_hash_rate, total_hash_rate, power_consumption))
                    await db.commit()
                    
                    return True, {
                        'amount': final_reward,
                        'hash_rate': total_hash_rate,
                        'power_consumption': power_consumption,
                        'efficiency': round(efficiency, 2),
                        'new_balance': new_balance
                    }
                
                return False, "エラーが発生しました"
                
        except Exception as e:
            economy_logger.error(f"Error in mining: {e}")
            return False, str(e)
    
    async def get_pc_build(self, guild_id, user_id):
        """ユーザーのPC構成を取得"""
        try:
            async with aiosqlite.connect(db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT pc_parts FROM user_economy 
                    WHERE guild_id = ? AND user_id = ?
                ''', (guild_id, user_id))
                result = await cursor.fetchone()
                
                if result and result[0]:
                    return json.loads(result[0])
                else:
                    return {}
                    
        except Exception as e:
            economy_logger.error(f"Error getting PC build: {e}")
            return {}
    
    async def update_pc_build(self, guild_id, user_id, pc_parts):
        """ユーザーのPC構成を更新"""
        try:
            async with aiosqlite.connect(db_manager.db_path) as db:
                # PC構成をJSONで保存
                pc_parts_json = json.dumps(pc_parts)
                
                await db.execute('''
                    UPDATE user_economy 
                    SET pc_parts = ?
                    WHERE guild_id = ? AND user_id = ?
                ''', (pc_parts_json, guild_id, user_id))
                await db.commit()
                
                return True
                
        except Exception as e:
            economy_logger.error(f"Error updating PC build: {e}")
            return False
    
    async def add_part_to_inventory(self, guild_id, user_id, part_type, part_name, part_data):
        """パーツをユーザーのインベントリに追加"""
        try:
            async with aiosqlite.connect(db_manager.db_path) as db:
                # インベントリから既存のパーツを取得
                cursor = await db.execute('''
                    SELECT inventory FROM user_economy 
                    WHERE guild_id = ? AND user_id = ?
                ''', (guild_id, user_id))
                result = await cursor.fetchone()
                
                if result and result[0]:
                    inventory = json.loads(result[0])
                else:
                    inventory = {}
                
                # パーツを追加
                if part_type not in inventory:
                    inventory[part_type] = {}
                
                if part_name in inventory[part_type]:
                    inventory[part_type][part_name] += 1
                else:
                    inventory[part_type][part_name] = 1
                
                # インベントリを更新
                inventory_json = json.dumps(inventory)
                await db.execute('''
                    UPDATE user_economy 
                    SET inventory = ?
                    WHERE guild_id = ? AND user_id = ?
                ''', (inventory_json, guild_id, user_id))
                await db.commit()
                
                return True
                
        except Exception as e:
            economy_logger.error(f"Error adding part to inventory: {e}")
            return False
    
    async def get_shop_items(self, guild_id):
        """ショップアイテム一覧取得"""
        try:
            async with aiosqlite.connect(db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT id, item_name, item_description, price, item_type, effect_value
                    FROM shop_items 
                    WHERE guild_id = ? AND is_active = 1
                    ORDER BY price ASC
                ''', (guild_id,))
                
                items = await cursor.fetchall()
                return items
                
        except Exception as e:
            economy_logger.error(f"Error getting shop items: {e}")
            return []
    
    async def buy_item(self, guild_id, user_id, item_id):
        """アイテム購入"""
        try:
            async with aiosqlite.connect(db_manager.db_path) as db:
                # アイテム情報取得
                cursor = await db.execute('''
                    SELECT item_name, price, item_type, effect_value
                    FROM shop_items 
                    WHERE id = ? AND guild_id = ? AND is_active = 1
                ''', (item_id, guild_id))
                item_data = await cursor.fetchone()
                
                if not item_data:
                    return False, "アイテムが見つかりません"
                
                item_name, price, item_type, effect_value = item_data
                
                # 残高確認
                current_balance = await self.get_user_balance(guild_id, user_id)
                if current_balance < price:
                    return False, f"残高不足です。必要: {price:,}{self.currency_symbol}"
                
                # 支払い処理
                success, new_balance = await self.update_balance(
                    guild_id, user_id, -price, "purchase", f"{item_name}を購入"
                )
                
                if not success:
                    return False, "購入処理でエラーが発生しました"
                
                # アイテム効果を適用
                if item_type == "mining_power":
                    await db.execute('''
                        UPDATE user_economy 
                        SET mining_power = mining_power + ?
                        WHERE guild_id = ? AND user_id = ?
                    ''', (effect_value, guild_id, user_id))
                elif item_type == "mining_auto":
                    await db.execute('''
                        UPDATE user_economy 
                        SET mining_auto = 1
                        WHERE guild_id = ? AND user_id = ?
                    ''', (guild_id, user_id))
                
                # アイテム所有記録
                await db.execute('''
                    INSERT INTO user_items (guild_id, user_id, item_id, quantity)
                    VALUES (?, ?, ?, 1)
                ''', (guild_id, user_id, item_id))
                
                await db.commit()
                
                return True, {
                    'item_name': item_name,
                    'price': price,
                    'new_balance': new_balance,
                    'effect': f"{item_type}: +{effect_value}"
                }
                
        except Exception as e:
            economy_logger.error(f"Error buying item: {e}")
            return False, str(e)
    
    async def get_leaderboard(self, guild_id, limit=10):
        """リーダーボード取得"""
        try:
            async with aiosqlite.connect(db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT user_id, balance, total_earned, mining_power
                    FROM user_economy 
                    WHERE guild_id = ?
                    ORDER BY balance DESC
                    LIMIT ?
                ''', (guild_id, limit))
                
                return await cursor.fetchall()
                
        except Exception as e:
            economy_logger.error(f"Error getting leaderboard: {e}")
            return []

# グローバルインスタンス
economy_system = EconomySystem()