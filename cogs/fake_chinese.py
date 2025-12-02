import discord
from discord.ext import commands
from discord import app_commands
import re
import random
import json
import os
from datetime import datetime
from typing import Optional

class ChineseCog(commands.Cog):
    """えせ中国語機能のCog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.violation_file = 'violations.json'
        
        # 違反記録ファイルの初期化
        if not os.path.exists(self.violation_file):
            with open(self.violation_file, 'w') as f:
                json.dump({}, f, indent=2)

    def get_guild_settings_path(self, guild_id):
        """サーバー設定ファイルのパスを取得"""
        return os.path.join('guild_settings', f'guild_settings_{guild_id}.json')

    def load_guild_settings(self, guild_id):
        """サーバー設定を読み込み"""
        settings_path = self.get_guild_settings_path(guild_id)
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_guild_settings(self, guild_id, settings):
        """サーバー設定を保存"""
        settings_path = self.get_guild_settings_path(guild_id)
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    def get_chinese_channels(self, guild_id):
        """サーバーのえせ中国語専用チャンネルのリストを取得"""
        settings = self.load_guild_settings(guild_id)
        return settings.get('chinese_channels', [])

    def get_global_chat_channel(self, guild_id):
        """サーバーのグローバルチャットチャンネルIDを取得"""
        settings = self.load_guild_settings(guild_id)
        return settings.get('global_chat_channel_id')

    def is_chinese_only(self, text):
        """テキストがえせ中国語ルールに準拠しているかチェック"""
        # URLを除外
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        # 絵文字を除外（Unicodeとカスタム絵文字）
        text = re.sub(r'<a?:[a-zA-Z0-9_]+:[0-9]+>', '', text)
        text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
        
        # 空白を除去
        text = text.strip()
        if not text:
            return True
        
        # 基本ルール
        # 1. ひらがな、カタカナは不許可
        if re.search(r'[ぁ-んァ-ン]', text):
            return False
        
        # 2. アルファベット単体は不許可（ただし複数文字の英単語は許可）
        alpha_words = re.findall(r'[a-zA-Z]+', text)
        if any(len(word) == 1 for word in alpha_words):
            return False
        
        # 3. 漢字、数字、記号は許可
        return True

    def load_violations(self):
        """違反記録を読み込み"""
        with open(self.violation_file, 'r') as f:
            return json.load(f)

    def add_violation(self, user_id, guild_id):
        """違反回数を追加し、10回達したらTrueを返す"""
        violations = self.load_violations()
        user_key = f"{user_id}_{guild_id}"
        
        if user_key not in violations:
            violations[user_key] = {"count": 0, "has_role": False}
        
        violations[user_key]["count"] += 1
        
        with open(self.violation_file, 'w') as f:
            json.dump(violations, f, indent=2)
        
        # 10回達したらTrueを返す
        return violations[user_key]["count"] >= 10

    def set_illegal_role_flag(self, user_id, guild_id):
        """不法移民ロール付与フラグを設定"""
        violations = self.load_violations()
        user_key = f"{user_id}_{guild_id}"
        
        if user_key in violations:
            violations[user_key]["has_role"] = True
            with open(self.violation_file, 'w') as f:
                json.dump(violations, f, indent=2)

    def has_illegal_role(self, user_id, guild_id):
        """不法移民ロールを持っているかチェック"""
        violations = self.load_violations()
        user_key = f"{user_id}_{guild_id}"
        return violations.get(user_key, {}).get("has_role", False)

    async def create_or_get_illegal_role(self, guild):
        """不法移民ロールを作成または取得"""
        role_name = "不法移民"
        
        # 既存のロールを探す
        for role in guild.roles:
            if role.name == role_name:
                return role
        
        # ロールが存在しない場合は作成
        try:
            role = await guild.create_role(
                name=role_name,
                color=discord.Color.red(),
                reason="えせ中国語違反10回による自動付与"
            )
            print(f"🚨 不法移民ロールを作成: {guild.name}")
            return role
        except Exception as e:
            print(f"❌ 不法移民ロール作成失敗: {guild.name} - {e}")
            return None

    # ====== えせ中国語ダイス機能 ======
    def parse_chinese_dice(self, text):
        """えせ中国語ダイス表記を解析"""
        # 数字の中国語マッピング
        chinese_nums = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '百': 100, '千': 1000, '万': 10000
        }
        
        # ダイス表記パターン: 一賽百 (1d100), 二賽六 (2d6), 三賽十 (3d10) など
        dice_pattern = r'([一二三四五六七八九十百千万]+)賽([一二三四五六七八九十百千万]+)'
        match = re.search(dice_pattern, text)
        
        if not match:
            return None
        
        dice_count_str = match.group(1)
        dice_sides_str = match.group(2)
        
        # 中国語数字を数値に変換
        dice_count = self.convert_chinese_number(dice_count_str, chinese_nums)
        dice_sides = self.convert_chinese_number(dice_sides_str, chinese_nums)
        
        return dice_count, dice_sides

    def convert_chinese_number(self, chinese_str, chinese_nums):
        """中国語数字を数値に変換"""
        if chinese_str in chinese_nums:
            return chinese_nums[chinese_str]
        
        # 複合数字の処理（例：二十 = 20, 三十五 = 35）
        total = 0
        current = 0
        
        for char in chinese_str:
            if char in chinese_nums:
                value = chinese_nums[char]
                if value >= 10:  # 十、百、千、万
                    if current == 0:
                        current = 1
                    total += current * value
                    current = 0
                else:
                    current = value
        
        total += current
        return total if total > 0 else 1

    def roll_dice(self, count, sides):
        """ダイスを振る"""
        if count <= 0 or sides <= 0:
            return None
        
        # 制限: 最大100個のダイス、最大10000面
        if count > 100 or sides > 10000:
            return None
        
        results = []
        for _ in range(count):
            results.append(random.randint(1, sides))
        
        return results

    def format_dice_result(self, dice_count, dice_sides, results):
        """ダイス結果をフォーマット"""
        total = sum(results)
        
        embed = discord.Embed(
            title="🎲 えせ中国語ダイス結果",
            color=discord.Color.blue()
        )
        
        # ダイス表記
        count_chinese = self.number_to_chinese(dice_count)
        sides_chinese = self.number_to_chinese(dice_sides)
        embed.add_field(
            name="🎯 ダイス",
            value=f"{count_chinese}賽{sides_chinese} ({dice_count}d{dice_sides})",
            inline=False
        )
        
        # 結果
        if len(results) == 1:
            embed.add_field(name="📊 結果", value=f"**{results[0]}**", inline=True)
        else:
            if len(results) <= 20:  # 20個以下なら個別表示
                results_str = " + ".join(map(str, results))
                embed.add_field(name="📊 各ダイス", value=results_str, inline=False)
            embed.add_field(name="📊 合計", value=f"**{total}**", inline=True)
            embed.add_field(name="📈 平均", value=f"{total/len(results):.1f}", inline=True)
        
        return embed

    def number_to_chinese(self, num):
        """数値を中国語数字に変換（簡易版）"""
        chinese_nums = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']
        
        if num <= 9:
            return chinese_nums[num] if num > 0 else '零'
        elif num == 10:
            return '十'
        elif num == 100:
            return '百'
        elif num == 1000:
            return '千'
        elif num == 10000:
            return '万'
        elif num < 20:
            return '十' + chinese_nums[num - 10]
        elif num < 100:
            tens = num // 10
            ones = num % 10
            result = chinese_nums[tens] + '十'
            if ones > 0:
                result += chinese_nums[ones]
            return result
        else:
            return str(num)  # 複雑な数字は数値のまま

    async def forward_global_message(self, message):
        """グローバルチャットにメッセージを転送"""
        content = message.content
        attachments = message.attachments
        
        # 転送用Embedを作成
        embed = discord.Embed(
            description=content,
            color=message.author.color,
            timestamp=message.created_at
        )
        embed.set_author(
            name=f"{message.author.display_name} ({message.guild.name})",
            icon_url=message.author.display_avatar.url
        )
        
        if attachments:
            if attachments[0].url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                embed.set_image(url=attachments[0].url)
            else:
                embed.add_field(name="📎 添付ファイル", value=attachments[0].url)
        
        # 他のサーバーに転送
        forwarded_count = 0
        for guild in self.bot.guilds:
            if guild.id == message.guild.id:
                continue
                
            target_channel_id = self.get_global_chat_channel(guild.id)
            if target_channel_id:
                channel = guild.get_channel(target_channel_id)
                if channel:
                    try:
                        await channel.send(embed=embed)
                        forwarded_count += 1
                    except Exception as e:
                        print(f"❌ グローバルチャット転送失敗: {guild.name} - {e}")
        
        print(f"🌐 グローバルチャット転送: {message.author.name} -> {forwarded_count}サーバー")

    async def forward_global_dice_result(self, message, dice_embed):
        """グローバルチャットにダイス結果を転送"""
        # 他のサーバーに転送
        forwarded_count = 0
        for guild in self.bot.guilds:
            if guild.id == message.guild.id:
                continue
                
            target_channel_id = self.get_global_chat_channel(guild.id)
            if target_channel_id:
                channel = guild.get_channel(target_channel_id)
                if channel:
                    try:
                        await channel.send(embed=dice_embed)
                        forwarded_count += 1
                    except Exception as e:
                        print(f"❌ グローバルダイス転送失敗: {guild.name} - {e}")
        
        print(f"🎲 グローバルダイス転送: {message.author.name} -> {forwarded_count}サーバー")

    # ====== スラッシュコマンド ======
    @app_commands.command(name="setchinesechannel", description="えせ中国語専用チャンネルを設定します（管理者限定）")
    @app_commands.describe(channel="えせ中国語専用にするチャンネル")
    async def setchinesechannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
            return
        
        await interaction.response.send_message("⏳ チャンネル設定を保存中...", ephemeral=True)
        
        settings = self.load_guild_settings(interaction.guild.id)
        
        if 'chinese_channels' not in settings:
            settings['chinese_channels'] = []
        
        if channel.id not in settings['chinese_channels']:
            settings['chinese_channels'].append(channel.id)
            self.save_guild_settings(interaction.guild.id, settings)
            
            await interaction.edit_original_response(content=f"✅ {channel.mention} をえせ中国語専用チャンネルに設定しました！\n⚠️ このチャンネルでは以下のルールが適用されます：\n❌ ひらがな、カタカナ、アルファベット（単体）\n✅ 漢字、数字、記号、絵文字、URL")
        else:
            await interaction.edit_original_response(content=f"⚠️ {channel.mention} は既にえせ中国語専用チャンネルです。")

    @app_commands.command(name="removechinesechannel", description="えせ中国語専用チャンネル設定を解除します（管理者限定）")
    @app_commands.describe(channel="設定を解除するチャンネル")
    async def removechinesechannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
            return
        
        await interaction.response.send_message("⏳ チャンネル設定を削除中...", ephemeral=True)
        
        settings = self.load_guild_settings(interaction.guild.id)
        
        if 'chinese_channels' in settings and channel.id in settings['chinese_channels']:
            settings['chinese_channels'].remove(channel.id)
            self.save_guild_settings(interaction.guild.id, settings)
            
            await interaction.edit_original_response(content=f"✅ {channel.mention} のえせ中国語専用チャンネル設定を解除しました！")
        else:
            await interaction.edit_original_response(content=f"⚠️ {channel.mention} はえせ中国語専用チャンネルに設定されていません。")

    @app_commands.command(name="lockchinesechannels", description="えせ中国語専用チャンネルをロックします（管理者限定）")
    async def lockchinesechannels(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
            return
        
        chinese_channels = self.get_chinese_channels(interaction.guild.id)
        if not chinese_channels:
            await interaction.response.send_message("❌ えせ中国語専用チャンネルが設定されていません。", ephemeral=True)
            return
        
        await interaction.response.send_message("⏳ チャンネルをロック中...", ephemeral=True)
        
        locked_count = 0
        failed_channels = []
        
        for channel_id in chinese_channels:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                try:
                    overwrites = channel.overwrites_for(interaction.guild.default_role)
                    overwrites.send_messages = False
                    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites)
                    locked_count += 1
                    print(f"🔒 チャンネルロック: {channel.name}")
                except Exception as e:
                    failed_channels.append(channel.name)
                    print(f"❌ チャンネルロック失敗: {channel.name} - {e}")
        
        result_msg = f"✅ {locked_count}個のえせ中国語専用チャンネルをロックしました！"
        if failed_channels:
            result_msg += f"\n⚠️ ロックに失敗したチャンネル: {', '.join(failed_channels)}"
        
        await interaction.edit_original_response(content=result_msg)

    @app_commands.command(name="unlockchinesechannels", description="えせ中国語専用チャンネルのロックを解除します（管理者限定）")
    async def unlockchinesechannels(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
            return
        
        chinese_channels = self.get_chinese_channels(interaction.guild.id)
        if not chinese_channels:
            await interaction.response.send_message("❌ えせ中国語専用チャンネルが設定されていません。", ephemeral=True)
            return
        
        await interaction.response.send_message("⏳ チャンネルロックを解除中...", ephemeral=True)
        
        unlocked_count = 0
        failed_channels = []
        
        for channel_id in chinese_channels:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                try:
                    overwrites = channel.overwrites_for(interaction.guild.default_role)
                    overwrites.send_messages = None
                    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrites)
                    unlocked_count += 1
                    print(f"🔓 チャンネルアンロック: {channel.name}")
                except Exception as e:
                    failed_channels.append(channel.name)
                    print(f"❌ チャンネルアンロック失敗: {channel.name} - {e}")
        
        result_msg = f"✅ {unlocked_count}個のえせ中国語専用チャンネルのロックを解除しました！"
        if failed_channels:
            result_msg += f"\n⚠️ アンロックに失敗したチャンネル: {', '.join(failed_channels)}"
        
        await interaction.edit_original_response(content=result_msg)

    @app_commands.command(name="setglobalchat", description="えせ中国語グローバルチャットチャンネルを設定します（管理者限定）")
    @app_commands.describe(channel="グローバルチャットにするチャンネル")
    async def setglobalchat(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
            return
        
        await interaction.response.send_message("⏳ グローバルチャット設定を保存中...", ephemeral=True)
        
        settings = self.load_guild_settings(interaction.guild.id)
        settings['global_chat_channel_id'] = channel.id
        self.save_guild_settings(interaction.guild.id, settings)
        
        await interaction.edit_original_response(content=f"✅ {channel.mention} をえせ中国語グローバルチャットチャンネルに設定しました！\n🌐 このチャンネルのメッセージは他のサーバーのグローバルチャットにも送信されます。")

    @app_commands.command(name="removeglobalchat", description="えせ中国語グローバルチャット設定を解除します（管理者限定）")
    async def removeglobalchat(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
            return
        
        await interaction.response.send_message("⏳ グローバルチャット設定を削除中...", ephemeral=True)
        
        settings = self.load_guild_settings(interaction.guild.id)
        
        if 'global_chat_channel_id' in settings:
            del settings['global_chat_channel_id']
            self.save_guild_settings(interaction.guild.id, settings)
            
            await interaction.edit_original_response(content="✅ えせ中国語グローバルチャット設定を解除しました！")
        else:
            await interaction.edit_original_response(content="⚠️ グローバルチャットが設定されていません。")

    @app_commands.command(name="checkviolations", description="違反回数を確認します")
    @app_commands.describe(member="確認するユーザー（省略可：自分の回数を確認）")
    async def checkviolations(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member if member else interaction.user
        
        violations = self.load_violations()
        user_key = f"{target.id}_{interaction.guild.id}"
        violation_data = violations.get(user_key, {"count": 0, "has_role": False})
        
        embed = discord.Embed(
            title="🚨 えせ中国語違反回数",
            color=discord.Color.red() if violation_data["has_role"] else discord.Color.orange()
        )
        embed.add_field(
            name="👤 対象ユーザー", 
            value=f"{target.mention} (`{target.id}`)", 
            inline=False
        )
        embed.add_field(
            name="📊 違反回数", 
            value=f"{violation_data['count']}/10回", 
            inline=True
        )
        embed.add_field(
            name="🏷️ ロール状態", 
            value="🚨 不法移民" if violation_data["has_role"] else "✅ 一般市民", 
            inline=True
        )
        
        if violation_data["count"] >= 7:
            embed.add_field(
                name="⚠️ 警告", 
                value=f"あと{10 - violation_data['count']}回で不法移民ロールが付与されます！", 
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="resetviolations", description="違反回数をリセットします（管理者限定）")
    @app_commands.describe(member="リセットするユーザー")
    async def resetviolations(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
            return
        
        await interaction.response.send_message("⏳ 違反記録をリセット中...", ephemeral=True)
        
        violations = self.load_violations()
        user_key = f"{member.id}_{interaction.guild.id}"
        
        if user_key in violations:
            if violations[user_key]["has_role"]:
                illegal_role = None
                for role in interaction.guild.roles:
                    if role.name == "不法移民":
                        illegal_role = role
                        break
                
                if illegal_role and illegal_role in member.roles:
                    try:
                        await member.remove_roles(illegal_role)
                        print(f"🔄 不法移民ロール削除: {member.display_name}")
                    except Exception as e:
                        print(f"❌ 不法移民ロール削除失敗: {e}")
            
            del violations[user_key]
            with open(self.violation_file, 'w') as f:
                json.dump(violations, f, indent=2)
            
            await interaction.edit_original_response(content=f"✅ {member.mention} の違反記録をリセットしました！")
        else:
            await interaction.edit_original_response(content=f"⚠️ {member.mention} の違反記録は見つかりませんでした。")

    @app_commands.command(name="dicehelp", description="えせ中国語ダイス機能の使い方を表示します")
    async def dicehelp(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎲 えせ中国語ダイス機能",
            description="えせ中国語専用チャンネルで使える中国語風ダイス機能です",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📝 基本の使い方",
            value="**ダイス個数賽面数** の形式で入力\n例：`一賽百` (1d100), `二賽六` (2d6)",
            inline=False
        )
        
        embed.add_field(
            name="🔢 数字の表記",
            value="一(1), 二(2), 三(3), 四(4), 五(5), 六(6), 七(7), 八(8), 九(9), 十(10), 百(100)",
            inline=False
        )
        
        embed.add_field(
            name="🎯 使用例",
            value="• `一賽六` → 1d6を振る\n• `二賽十` → 2d10を振る\n• `三賽百` → 3d100を振る\n• `十賽六` → 10d6を振る",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ 制限事項",
            value="• 最大100個のダイス\n• 最大10000面のダイス\n• えせ中国語専用チャンネルでのみ動作",
            inline=False
        )
        
        embed.add_field(
            name="🌐 グローバルチャット",
            value="グローバルチャットでダイスを振ると、他のサーバーにも結果が転送されます",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ====== イベントハンドラ ======
    @commands.Cog.listener()
    async def on_message(self, message):
        # BOT自身のメッセージは無視
        if message.author.bot:
            return
        
        # Guild が None の場合は処理しない
        if message.guild is None:
            return
        
        # 空のメッセージやシステムメッセージは無視
        if not message.content.strip():
            return
        
        # えせ中国語専用チャンネルかチェック
        chinese_channels = self.get_chinese_channels(message.guild.id)
        global_chat_channel_id = self.get_global_chat_channel(message.guild.id)
        
        if message.channel.id in chinese_channels:
            # えせ中国語ダイス機能をチェック
            dice_result = self.parse_chinese_dice(message.content)
            if dice_result:
                dice_count, dice_sides = dice_result
                results = self.roll_dice(dice_count, dice_sides)
                
                if results:
                    embed = self.format_dice_result(dice_count, dice_sides, results)
                    embed.set_author(
                        name=f"{message.author.display_name}",
                        icon_url=message.author.display_avatar.url
                    )
                    await message.channel.send(embed=embed)
                    print(f"🎲 ダイス実行: {message.author.name} - {dice_count}d{dice_sides}")
                    
                    # グローバルチャットの場合、ダイス結果を転送
                    if global_chat_channel_id and message.channel.id == global_chat_channel_id:
                        await self.forward_global_dice_result(message, embed)
                    return
            
            # メッセージが漢字のみかチェック
            is_valid = self.is_chinese_only(message.content)
            
            if not is_valid:
                try:
                    await message.delete()
                    print(f"🗑️ 中国語フィルター: {message.author.name}のメッセージを削除: {message.content}")
                    
                    # 違反回数を追加
                    should_get_role = self.add_violation(message.author.id, message.guild.id)
                    
                    if should_get_role and not self.has_illegal_role(message.author.id, message.guild.id):
                        illegal_role = await self.create_or_get_illegal_role(message.guild)
                        if illegal_role:
                            try:
                                member = message.guild.get_member(message.author.id)
                                if member:
                                    await member.add_roles(illegal_role)
                                    self.set_illegal_role_flag(message.author.id, message.guild.id)
                                    print(f"🚨 不法移民ロール付与: {member.display_name} (違反10回達成)")
                                    
                                    try:
                                        await member.send(f"🚨 **{message.guild.name}** でえせ中国語違反が10回に達しました。\n「不法移民」ロールが付与されました。")
                                    except:
                                        pass
                            except Exception as e:
                                print(f"❌ 不法移民ロール付与失敗: {e}")
                                
                except discord.errors.NotFound:
                    pass
                except discord.errors.Forbidden:
                    pass
        
        # グローバルチャット機能
        if global_chat_channel_id and message.channel.id == global_chat_channel_id:
            # えせ中国語ダイス機能をチェック
            dice_result = self.parse_chinese_dice(message.content)
            if dice_result:
                dice_count, dice_sides = dice_result
                results = self.roll_dice(dice_count, dice_sides)
                
                if results:
                    embed = self.format_dice_result(dice_count, dice_sides, results)
                    embed.set_author(
                        name=f"{message.author.display_name}",
                        icon_url=message.author.display_avatar.url
                    )
                    await message.channel.send(embed=embed)
                    print(f"🎲 グローバルダイス実行: {message.author.name} - {dice_count}d{dice_sides}")
                    
                    await self.forward_global_dice_result(message, embed)
                    return
            
            # メッセージが漢字のみかチェック
            is_valid = self.is_chinese_only(message.content)
            
            if not is_valid:
                try:
                    await message.delete()
                    print(f"🗑️ グローバルチャット中国語フィルター: {message.author.name}のメッセージを削除: {message.content}")
                    
                    # 違反回数を追加
                    should_get_role = self.add_violation(message.author.id, message.guild.id)
                    
                    if should_get_role and not self.has_illegal_role(message.author.id, message.guild.id):
                        illegal_role = await self.create_or_get_illegal_role(message.guild)
                        if illegal_role:
                            try:
                                member = message.guild.get_member(message.author.id)
                                if member:
                                    await member.add_roles(illegal_role)
                                    self.set_illegal_role_flag(message.author.id, message.guild.id)
                                    print(f"🚨 不法移民ロール付与: {member.display_name} (違反10回達成)")
                                    
                                    try:
                                        await member.send(f"🚨 **{message.guild.name}** でえせ中国語違反が10回に達しました。\n「不法移民」ロールが付与されました。")
                                    except:
                                        pass
                            except Exception as e:
                                print(f"❌ 不法移民ロール付与失敗: {e}")
                                
                except discord.errors.NotFound:
                    pass
                except discord.errors.Forbidden:
                    pass
                return
            
            # 他のサーバーのグローバルチャットにメッセージを転送
            await self.forward_global_message(message)

    # ====== チャンネルロック機能 ======
    async def lock_chinese_channels(self):
        """全サーバーのえせ中国語専用チャンネルをロック"""
        total_locked = 0
        for guild in self.bot.guilds:
            chinese_channels = self.get_chinese_channels(guild.id)
            for channel_id in chinese_channels:
                channel = guild.get_channel(channel_id)
                if channel:
                    try:
                        overwrites = channel.overwrites_for(guild.default_role)
                        overwrites.send_messages = False
                        await channel.set_permissions(guild.default_role, overwrite=overwrites)
                        total_locked += 1
                        print(f"🔒 自動ロック: {guild.name} - {channel.name}")
                    except Exception as e:
                        print(f"❌ 自動ロック失敗: {guild.name} - {channel.name} - {e}")
        
        if total_locked > 0:
            print(f"🔒 合計 {total_locked}個のチャンネルを自動ロックしました")

    async def unlock_chinese_channels(self):
        """全サーバーのえせ中国語専用チャンネルのロックを解除"""
        total_unlocked = 0
        for guild in self.bot.guilds:
            chinese_channels = self.get_chinese_channels(guild.id)
            for channel_id in chinese_channels:
                channel = guild.get_channel(channel_id)
                if channel:
                    try:
                        overwrites = channel.overwrites_for(guild.default_role)
                        overwrites.send_messages = None
                        await channel.set_permissions(guild.default_role, overwrite=overwrites)
                        total_unlocked += 1
                        print(f"🔓 自動アンロック: {guild.name} - {channel.name}")
                    except Exception as e:
                        print(f"❌ 自動アンロック失敗: {guild.name} - {channel.name} - {e}")
        
        if total_unlocked > 0:
            print(f"🔓 合計 {total_unlocked}個のチャンネルを自動アンロックしました")

async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(ChineseCog(bot))