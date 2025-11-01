"""
RTKS Discord Bot - メインボットファイル (モジュール化版)
多機能Discordボット - モジュール構造
"""

__version__ = "2.0.0"
__author__ = "YukiSannn"
__license__ = "MIT"

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

# 設定とデータベースのインポート
try:
    import config
    from database import db_manager
    from economy import EconomySystem
    from keep_alive import keep_alive
except ImportError as e:
    print(f"❌ モジュールのインポートに失敗しました: {e}")
    print("必要なファイルが存在するか確認してください。")
    exit(1)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'bot_log_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
bot_logger = logging.getLogger('bot')

# Botの設定
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# データベース有効性フラグ
DB_ENABLED = False

@bot.event
async def on_ready():
    """ボット起動時の処理"""
    global DB_ENABLED
    
    bot_logger.info("ボット開始")
    
    # データベース初期化
    try:
        await db_manager.initialize()
        DB_ENABLED = db_manager.is_initialized()
        if DB_ENABLED:
            bot_logger.info("データベースシステム初期化完了")
        else:
            bot_logger.warning("データベースが利用できません")
    except Exception as e:
        bot_logger.error(f"データベース初期化エラー: {e}")
        DB_ENABLED = False

    # Keep-alive サーバー起動
    try:
        if hasattr(config, 'KEEP_ALIVE_ENABLED') and config.KEEP_ALIVE_ENABLED:
            keep_alive()
            bot_logger.info("Keep-alive server started")
    except Exception as e:
        bot_logger.error(f"Keep-alive server error: {e}")

    # ボット情報表示
    print(f"✅ Bot起動完了: {bot.user}")
    print(f"📊 接続サーバー数: {len(bot.guilds)}")
    
    for guild in bot.guilds:
        print(f"🏰 サーバー: {guild.name} (ID: {guild.id})")

    # コマンド同期
    try:
        print("🔄 スラッシュコマンドを同期中...")
        synced = await bot.tree.sync()
        print(f"✅ スラッシュコマンドを同期しました: {len(synced)}個のコマンド")
        
        # コマンド一覧表示
        for command in synced:
            print(f"  - /{command.name}: {command.description}")
            
    except Exception as e:
        bot_logger.error(f"コマンド同期エラー: {e}")

    # 永続化ビューの準備
    try:
        from modules.auth import PersistentAuthView
        bot.add_view(PersistentAuthView())
        bot_logger.info("🔄 認証パネルの永続化ビューを準備しました")
    except Exception as e:
        bot_logger.error(f"永続化ビュー準備エラー: {e}")

    print("🚀 ボットが完全に準備完了しました！")

async def load_modules():
    """全モジュールを読み込み"""
    modules = [
        'modules.music',           # 音楽・音声機能
        'modules.auth',            # 認証・メンション管理
        'modules.roles',           # ロール管理
        'modules.channel_management',  # チャンネル管理
        'modules.introduction',    # 自己紹介システム
        'modules.voice',           # VOICEVOX機能
    ]
    
    loaded_modules = []
    failed_modules = []
    
    for module in modules:
        try:
            await bot.load_extension(module)
            loaded_modules.append(module)
            bot_logger.info(f"✅ モジュール読み込み成功: {module}")
        except Exception as e:
            failed_modules.append((module, str(e)))
            bot_logger.error(f"❌ モジュール読み込み失敗: {module} - {e}")
    
    print(f"\n📦 モジュール読み込み結果:")
    print(f"✅ 成功: {len(loaded_modules)}個")
    for module in loaded_modules:
        print(f"  - {module}")
    
    if failed_modules:
        print(f"❌ 失敗: {len(failed_modules)}個")
        for module, error in failed_modules:
            print(f"  - {module}: {error}")

# ===== 経済システムコマンド =====
economy_system = EconomySystem()

@bot.tree.command(name="balance", description="自分の残高を確認します")
async def balance(interaction: discord.Interaction):
    """残高確認コマンド"""
    if not DB_ENABLED:
        await interaction.response.send_message("❌ 経済システムは利用できません。", ephemeral=True)
        return
    
    try:
        balance_amount = await economy_system.get_balance(interaction.guild.id, interaction.user.id)
        
        embed = discord.Embed(
            title="💰 残高確認",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="現在の残高", value=f"{balance_amount:,} コイン", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        bot_logger.error(f"残高確認エラー: {e}")
        await interaction.response.send_message("❌ 残高確認中にエラーが発生しました。", ephemeral=True)

@bot.tree.command(name="daily", description="デイリー報酬を受け取ります")
async def daily(interaction: discord.Interaction):
    """デイリー報酬コマンド"""
    if not DB_ENABLED:
        await interaction.response.send_message("❌ 経済システムは利用できません。", ephemeral=True)
        return
    
    try:
        reward = await economy_system.claim_daily_reward(interaction.guild.id, interaction.user.id)
        
        if reward > 0:
            embed = discord.Embed(
                title="🎁 デイリー報酬",
                description=f"{reward:,} コインを獲得しました！",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        else:
            embed = discord.Embed(
                title="⏰ デイリー報酬",
                description="デイリー報酬は24時間に1回まで受け取れます。",
                color=0xff9900,
                timestamp=datetime.now()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        bot_logger.error(f"デイリー報酬エラー: {e}")
        await interaction.response.send_message("❌ デイリー報酬の受け取り中にエラーが発生しました。", ephemeral=True)

@bot.tree.command(name="mine", description="マイニングを実行して報酬を得ます")
async def mine(interaction: discord.Interaction):
    """マイニングコマンド"""
    if not DB_ENABLED:
        await interaction.response.send_message("❌ 経済システムは利用できません。", ephemeral=True)
        return
    
    try:
        reward = await economy_system.mine_coins(interaction.guild.id, interaction.user.id)
        
        if reward > 0:
            embed = discord.Embed(
                title="⛏️ マイニング成功",
                description=f"{reward:,} コインを採掘しました！",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        else:
            embed = discord.Embed(
                title="⏰ マイニング",
                description="マイニングは1時間に1回まで実行できます。",
                color=0xff9900,
                timestamp=datetime.now()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        bot_logger.error(f"マイニングエラー: {e}")
        await interaction.response.send_message("❌ マイニング中にエラーが発生しました。", ephemeral=True)

@bot.tree.command(name="shop", description="ショップでアイテムを確認・購入します")
async def shop(interaction: discord.Interaction):
    """ショップコマンド"""
    if not DB_ENABLED:
        await interaction.response.send_message("❌ 経済システムは利用できません。", ephemeral=True)
        return
    
    try:
        items = await economy_system.get_shop_items(interaction.guild.id)
        
        embed = discord.Embed(
            title="🛒 ショップ",
            color=0x0099ff,
            timestamp=datetime.now()
        )
        
        if items:
            for item in items[:10]:  # 最大10個表示
                embed.add_field(
                    name=f"{item['name']} - {item['price']:,} コイン",
                    value=item['description'],
                    inline=False
                )
        else:
            embed.add_field(name="商品", value="現在、販売中の商品はありません。", inline=False)
        
        embed.set_footer(text="購入するには /buy <アイテム名> を使用してください")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        bot_logger.error(f"ショップ表示エラー: {e}")
        await interaction.response.send_message("❌ ショップの表示中にエラーが発生しました。", ephemeral=True)

@bot.tree.command(name="buy", description="ショップでアイテムを購入します")
@app_commands.describe(item_name="購入するアイテム名")
async def buy(interaction: discord.Interaction, item_name: str):
    """アイテム購入コマンド"""
    if not DB_ENABLED:
        await interaction.response.send_message("❌ 経済システムは利用できません。", ephemeral=True)
        return
    
    try:
        success = await economy_system.buy_item(interaction.guild.id, interaction.user.id, item_name)
        
        if success:
            embed = discord.Embed(
                title="✅ 購入完了",
                description=f"**{item_name}** を購入しました！",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        else:
            embed = discord.Embed(
                title="❌ 購入失敗",
                description="アイテムが見つからないか、残高が不足しています。",
                color=0xff0000,
                timestamp=datetime.now()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        bot_logger.error(f"アイテム購入エラー: {e}")
        await interaction.response.send_message("❌ アイテム購入中にエラーが発生しました。", ephemeral=True)

@bot.tree.command(name="leaderboard", description="サーバーの経済ランキングを表示します")
async def leaderboard(interaction: discord.Interaction):
    """ランキング表示コマンド"""
    if not DB_ENABLED:
        await interaction.response.send_message("❌ 経済システムは利用できません。", ephemeral=True)
        return
    
    try:
        top_users = await economy_system.get_leaderboard(interaction.guild.id, limit=10)
        
        embed = discord.Embed(
            title="🏆 経済ランキング TOP10",
            color=0xffd700,
            timestamp=datetime.now()
        )
        
        if top_users:
            ranking_text = []
            for i, (user_id, balance) in enumerate(top_users, 1):
                user = bot.get_user(user_id)
                name = user.display_name if user else f"ユーザー{user_id}"
                
                if i == 1:
                    emoji = "🥇"
                elif i == 2:
                    emoji = "🥈"
                elif i == 3:
                    emoji = "🥉"
                else:
                    emoji = f"{i}."
                    
                ranking_text.append(f"{emoji} **{name}** - {balance:,} コイン")
            
            embed.add_field(name="ランキング", value="\n".join(ranking_text), inline=False)
        else:
            embed.add_field(name="ランキング", value="まだデータがありません。", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        bot_logger.error(f"ランキング表示エラー: {e}")
        await interaction.response.send_message("❌ ランキング表示中にエラーが発生しました。", ephemeral=True)

# ===== ダイスヘルプコマンド =====
@bot.tree.command(name="dicehelp", description="えせ中国語ダイス機能の使い方を表示します")
async def dicehelp(interaction: discord.Interaction):
    """ダイス機能のヘルプ表示"""
    embed = discord.Embed(
        title="🎲 えせ中国語ダイス機能",
        description="メッセージ内でダイスロールができます！",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="基本的な使い方",
        value="メッセージに `#d数字` を含めると自動でダイスロールされます",
        inline=False
    )
    
    embed.add_field(
        name="例",
        value="`こんにちは！ #d6 で遊びましょう` → 1-6の範囲でランダムな数字",
        inline=False
    )
    
    embed.add_field(
        name="対応形式",
        value="- `#d6` : 1-6のダイス\n- `#d20` : 1-20のダイス\n- `#d100` : 1-100のダイス",
        inline=False
    )
    
    embed.set_footer(text="えせ中国語チャンネルで利用できます")
    
    await interaction.response.send_message(embed=embed)

async def main():
    """メイン実行関数"""
    try:
        # モジュール読み込み
        await load_modules()
        
        # Botトークン確認
        if not hasattr(config, 'DISCORD_TOKEN') or not config.DISCORD_TOKEN:
            print("❌ DISCORD_TOKEN が設定されていません。")
            print("config.py または .env ファイルを確認してください。")
            return
        
        # Bot起動
        await bot.start(config.DISCORD_TOKEN)
        
    except discord.LoginFailure:
        print("❌ Discord へのログインに失敗しました。トークンを確認してください。")
    except Exception as e:
        print(f"❌ ボット起動エラー: {e}")
        bot_logger.error(f"ボット起動エラー: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🔄 ボットを停止しています...")
        bot_logger.info("ボット停止")
    except Exception as e:
        print(f"❌ 致命的エラー: {e}")
        bot_logger.critical(f"致命的エラー: {e}")
    finally:
        print("👋 ボットが停止しました。")