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
import aiosqlite
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

@bot.tree.command(name="mine", description="PCでマイニングを実行して報酬を得ます")
async def mine(interaction: discord.Interaction):
    """PCパーツベースマイニングコマンド"""
    if not DB_ENABLED:
        await interaction.response.send_message("❌ 経済システムは利用できません。", ephemeral=True)
        return
    
    try:
        success, result = await economy_system.mining_reward(interaction.guild.id, interaction.user.id)
        
        if success:
            embed = discord.Embed(
                title="⛏️ PCマイニング成功",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            
            embed.add_field(
                name="💰 獲得報酬",
                value=f"{result['amount']:,} {economy_system.currency_symbol}",
                inline=True
            )
            embed.add_field(
                name="⚡ ハッシュレート",
                value=f"{result['hash_rate']} MH/s",
                inline=True
            )
            embed.add_field(
                name="🔌 消費電力",
                value=f"{result['power_consumption']}W",
                inline=True
            )
            embed.add_field(
                name="📊 効率",
                value=f"{result['efficiency']:.2f}",
                inline=True
            )
            embed.add_field(
                name="💳 残高",
                value=f"{result['new_balance']:,} {economy_system.currency_symbol}",
                inline=True
            )
            
            if result['hash_rate'] == 1:
                embed.add_field(
                    name="💡 ヒント",
                    value="PCパーツを購入してハッシュレートを向上させましょう！\n`/pc-shop` でパーツを確認できます。",
                    inline=False
                )
        else:
            embed = discord.Embed(
                title="❌ マイニングエラー",
                description=result,
                color=0xff0000,
                timestamp=datetime.now()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        bot_logger.error(f"マイニングエラー: {e}")
        await interaction.response.send_message("❌ マイニング中にエラーが発生しました。", ephemeral=True)

@bot.tree.command(name="pc-shop", description="PCパーツショップでランダムパーツを購入します")
@app_commands.describe(
    part_type="購入するパーツの種類",
    quantity="購入する個数"
)
@app_commands.choices(part_type=[
    app_commands.Choice(name="GPU (グラフィックボード)", value="gpus"),
    app_commands.Choice(name="CPU (プロセッサー)", value="cpus"),
    app_commands.Choice(name="マザーボード", value="motherboards"),
    app_commands.Choice(name="電源ユニット", value="psus")
])
async def pc_shop(interaction: discord.Interaction, part_type: str, quantity: int = 1):
    """PCパーツショップコマンド"""
    if not DB_ENABLED:
        await interaction.response.send_message("❌ 経済システムは利用できません。", ephemeral=True)
        return
    
    if quantity < 1 or quantity > 10:
        await interaction.response.send_message("❌ 購入数は1〜10の間で指定してください。", ephemeral=True)
        return
    
    try:
        from modules.pc_parts import PCPartsData
        
        # 基本価格設定
        base_prices = {
            "gpus": 100000,
            "cpus": 80000,
            "motherboards": 50000,
            "psus": 30000
        }
        
        total_cost = base_prices[part_type] * quantity
        
        # 残高確認
        balance = await economy_system.get_user_balance(interaction.guild.id, interaction.user.id)
        if balance < total_cost:
            embed = discord.Embed(
                title="💸 残高不足",
                description=f"必要: {total_cost:,} {economy_system.currency_symbol}\n現在: {balance:,} {economy_system.currency_symbol}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # パーツを抽選
        acquired_parts = []
        for _ in range(quantity):
            part_name, part_data = PCPartsData.get_random_part(part_type)
            acquired_parts.append((part_name, part_data))
            
            # インベントリに追加
            await economy_system.add_part_to_inventory(
                interaction.guild.id, interaction.user.id, part_type, part_name, part_data
            )
        
        # 支払い処理
        await economy_system.update_balance(
            interaction.guild.id, interaction.user.id, -total_cost, "purchase", 
            f"PCパーツ購入 ({part_type})"
        )
        
        # 結果表示
        embed = discord.Embed(
            title="🛒 PCパーツ購入完了",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        
        embed.add_field(
            name="💰 支払い",
            value=f"{total_cost:,} {economy_system.currency_symbol}",
            inline=True
        )
        
        new_balance = balance - total_cost
        embed.add_field(
            name="💳 残高",
            value=f"{new_balance:,} {economy_system.currency_symbol}",
            inline=True
        )
        
        # 獲得パーツ詳細
        for i, (part_name, part_data) in enumerate(acquired_parts):
            tier = part_data["tier"]
            rarity_emoji = PCPartsData.RARITY_EMOJIS[tier]
            
            if part_type == "gpus":
                details = f"ハッシュレート: {part_data['hash_rate']} MH/s\n消費電力: {part_data['power']}W\nVRAM: {part_data['memory']}"
            elif part_type == "cpus":
                details = f"ハッシュレート: {part_data['hash_rate']} MH/s\n消費電力: {part_data['power']}W\nコア: {part_data['cores']}"
            elif part_type == "motherboards":
                details = f"最大GPU: {part_data['max_gpus']}枚\nソケット: {part_data['socket']}"
            else:  # psus
                details = f"出力: {part_data['wattage']}W\n効率: {part_data['efficiency']}"
            
            embed.add_field(
                name=f"{rarity_emoji} {part_name}",
                value=details,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        bot_logger.error(f"PCショップエラー: {e}")
        await interaction.response.send_message("❌ PCパーツ購入中にエラーが発生しました。", ephemeral=True)

@bot.tree.command(name="pc-build", description="PC構成を確認・編集します")
async def pc_build(interaction: discord.Interaction):
    """PC構成確認コマンド"""
    if not DB_ENABLED:
        await interaction.response.send_message("❌ 経済システムは利用できません。", ephemeral=True)
        return
    
    try:
        from modules.pc_parts import PCPartsData
        
        # 現在のPC構成を取得
        pc_build = await economy_system.get_pc_build(interaction.guild.id, interaction.user.id)
        
        embed = discord.Embed(
            title="🖥️ あなたのPC構成",
            color=0x0080ff,
            timestamp=datetime.now()
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        
        if not pc_build:
            embed.description = "PC構成が設定されていません。\n`/pc-inventory` でパーツを確認し、`/pc-assemble` で組み立てましょう！"
        else:
            # GPU
            if "gpus" in pc_build and pc_build["gpus"]:
                gpu_list = []
                for gpu_name, quantity in pc_build["gpus"].items():
                    if gpu_name in PCPartsData.GPUS:
                        gpu_data = PCPartsData.GPUS[gpu_name]
                        tier_emoji = PCPartsData.RARITY_EMOJIS[gpu_data["tier"]]
                        gpu_list.append(f"{tier_emoji} {gpu_name} x{quantity}")
                embed.add_field(name="🎮 GPU", value="\n".join(gpu_list) if gpu_list else "なし", inline=False)
            
            # CPU
            if "cpu" in pc_build and pc_build["cpu"]:
                cpu_name = pc_build["cpu"]
                if cpu_name in PCPartsData.CPUS:
                    cpu_data = PCPartsData.CPUS[cpu_name]
                    tier_emoji = PCPartsData.RARITY_EMOJIS[cpu_data["tier"]]
                    embed.add_field(name="🔧 CPU", value=f"{tier_emoji} {cpu_name}", inline=True)
            
            # マザーボード
            if "motherboard" in pc_build and pc_build["motherboard"]:
                mb_name = pc_build["motherboard"]
                if mb_name in PCPartsData.MOTHERBOARDS:
                    mb_data = PCPartsData.MOTHERBOARDS[mb_name]
                    tier_emoji = PCPartsData.RARITY_EMOJIS[mb_data["tier"]]
                    embed.add_field(name="🔌 マザーボード", value=f"{tier_emoji} {mb_name}", inline=True)
            
            # 電源
            if "psu" in pc_build and pc_build["psu"]:
                psu_name = pc_build["psu"]
                if psu_name in PCPartsData.PSUS:
                    psu_data = PCPartsData.PSUS[psu_name]
                    tier_emoji = PCPartsData.RARITY_EMOJIS[psu_data["tier"]]
                    embed.add_field(name="⚡ 電源", value=f"{tier_emoji} {psu_name}", inline=True)
            
            # 性能統計
            total_hash_rate = PCPartsData.calculate_total_hash_rate(pc_build)
            total_power = PCPartsData.calculate_power_consumption(pc_build)
            efficiency = total_hash_rate / max(total_power, 1) if total_power > 0 else 0
            
            embed.add_field(
                name="📊 性能統計",
                value=f"**ハッシュレート**: {total_hash_rate} MH/s\n**消費電力**: {total_power}W\n**効率**: {efficiency:.2f}",
                inline=False
            )
            
            # 構成チェック
            is_valid, message = PCPartsData.is_build_valid(pc_build)
            if not is_valid:
                embed.add_field(
                    name="⚠️ 構成の問題",
                    value=message,
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        bot_logger.error(f"PC構成確認エラー: {e}")
        await interaction.response.send_message("❌ PC構成の確認中にエラーが発生しました。", ephemeral=True)

@bot.tree.command(name="pc-inventory", description="所有しているPCパーツの一覧を確認します")
async def pc_inventory(interaction: discord.Interaction):
    """PCパーツインベントリコマンド"""
    if not DB_ENABLED:
        await interaction.response.send_message("❌ 経済システムは利用できません。", ephemeral=True)
        return
    
    try:
        from modules.pc_parts import PCPartsData
        import json
        
        # インベントリ取得
        async with aiosqlite.connect(db_manager.db_path) as db:
            cursor = await db.execute('''
                SELECT inventory FROM user_economy 
                WHERE guild_id = ? AND user_id = ?
            ''', (interaction.guild.id, interaction.user.id))
            result = await cursor.fetchone()
        
        if result and result[0]:
            inventory = json.loads(result[0])
        else:
            inventory = {}
        
        embed = discord.Embed(
            title="🎒 PCパーツインベントリ",
            color=0x00ff80,
            timestamp=datetime.now()
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        
        if not inventory:
            embed.description = "パーツを所有していません。\n`/pc-shop` でパーツを購入しましょう！"
        else:
            for part_type, parts in inventory.items():
                if not parts:
                    continue
                
                part_list = []
                for part_name, quantity in parts.items():
                    # パーツデータ取得
                    parts_dict = getattr(PCPartsData, part_type.upper(), {})
                    if part_name in parts_dict:
                        part_data = parts_dict[part_name]
                        tier_emoji = PCPartsData.RARITY_EMOJIS[part_data["tier"]]
                        part_list.append(f"{tier_emoji} {part_name} x{quantity}")
                
                if part_list:
                    type_names = {
                        "gpus": "🎮 GPU",
                        "cpus": "🔧 CPU", 
                        "motherboards": "🔌 マザーボード",
                        "psus": "⚡ 電源"
                    }
                    embed.add_field(
                        name=type_names.get(part_type, part_type),
                        value="\n".join(part_list),
                        inline=False
                    )
        
        embed.add_field(
            name="💡 ヒント",
            value="`/pc-assemble` でパーツを組み立ててマイニング性能を向上させましょう！",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        bot_logger.error(f"PCインベントリエラー: {e}")
        await interaction.response.send_message("❌ インベントリの確認中にエラーが発生しました。", ephemeral=True)

@bot.tree.command(name="pc-assemble", description="PCパーツを組み立てて構成を作成します")
@app_commands.describe(
    gpu="使用するGPU (複数枚可)",
    cpu="使用するCPU",
    motherboard="使用するマザーボード",
    psu="使用する電源ユニット"
)
async def pc_assemble(interaction: discord.Interaction, gpu: str = None, cpu: str = None, motherboard: str = None, psu: str = None):
    """PC組み立てコマンド"""
    if not DB_ENABLED:
        await interaction.response.send_message("❌ 経済システムは利用できません。", ephemeral=True)
        return
    
    try:
        from modules.pc_parts import PCPartsData
        import json
        
        # インベントリ取得
        async with aiosqlite.connect(db_manager.db_path) as db:
            cursor = await db.execute('''
                SELECT inventory FROM user_economy 
                WHERE guild_id = ? AND user_id = ?
            ''', (interaction.guild.id, interaction.user.id))
            result = await cursor.fetchone()
        
        if result and result[0]:
            inventory = json.loads(result[0])
        else:
            inventory = {}
        
        new_build = {}
        errors = []
        
        # GPU設定
        if gpu:
            gpu_names = [name.strip() for name in gpu.split(",")]
            gpu_dict = {}
            for gpu_name in gpu_names:
                if "gpus" not in inventory or gpu_name not in inventory["gpus"]:
                    errors.append(f"GPU '{gpu_name}' を所有していません")
                elif inventory["gpus"][gpu_name] <= 0:
                    errors.append(f"GPU '{gpu_name}' の在庫がありません")
                else:
                    gpu_dict[gpu_name] = gpu_dict.get(gpu_name, 0) + 1
            
            if gpu_dict:
                new_build["gpus"] = gpu_dict
        
        # CPU設定
        if cpu:
            if "cpus" not in inventory or cpu not in inventory["cpus"]:
                errors.append(f"CPU '{cpu}' を所有していません")
            elif inventory["cpus"][cpu] <= 0:
                errors.append(f"CPU '{cpu}' の在庫がありません")
            else:
                new_build["cpu"] = cpu
        
        # マザーボード設定
        if motherboard:
            if "motherboards" not in inventory or motherboard not in inventory["motherboards"]:
                errors.append(f"マザーボード '{motherboard}' を所有していません")
            elif inventory["motherboards"][motherboard] <= 0:
                errors.append(f"マザーボード '{motherboard}' の在庫がありません")
            else:
                new_build["motherboard"] = motherboard
        
        # 電源設定
        if psu:
            if "psus" not in inventory or psu not in inventory["psus"]:
                errors.append(f"電源ユニット '{psu}' を所有していません")
            elif inventory["psus"][psu] <= 0:
                errors.append(f"電源ユニット '{psu}' の在庫がありません")
            else:
                new_build["psu"] = psu
        
        if errors:
            embed = discord.Embed(
                title="❌ 組み立てエラー",
                description="\n".join(errors),
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not new_build:
            embed = discord.Embed(
                title="❌ パーツが指定されていません",
                description="組み立てるパーツを指定してください。\n例: `/pc-assemble gpu:RTX 4090 cpu:i9-13900K`",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 構成の有効性チェック
        is_valid, message = PCPartsData.is_build_valid(new_build)
        if not is_valid:
            embed = discord.Embed(
                title="❌ 構成エラー",
                description=message,
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 構成を保存
        success = await economy_system.update_pc_build(interaction.guild.id, interaction.user.id, new_build)
        
        if success:
            # 性能計算
            total_hash_rate = PCPartsData.calculate_total_hash_rate(new_build)
            total_power = PCPartsData.calculate_power_consumption(new_build)
            efficiency = total_hash_rate / max(total_power, 1) if total_power > 0 else 0
            
            embed = discord.Embed(
                title="🔧 PC組み立て完了",
                description="新しいPC構成が保存されました！",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            
            embed.add_field(
                name="📊 性能統計",
                value=f"**ハッシュレート**: {total_hash_rate} MH/s\n**消費電力**: {total_power}W\n**効率**: {efficiency:.2f}",
                inline=False
            )
            
            embed.add_field(
                name="💡 次のステップ",
                value="`/mine` コマンドで新しい構成でマイニングを開始できます！",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="❌ 保存エラー",
                description="PC構成の保存中にエラーが発生しました。",
                color=0xff0000
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        bot_logger.error(f"PC組み立てエラー: {e}")
        await interaction.response.send_message("❌ PC組み立て中にエラーが発生しました。", ephemeral=True)

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