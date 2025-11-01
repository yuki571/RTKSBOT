"""
RTKS Discord Bot - チャンネル管理モジュール
えせ中国語機能、チャンネル設定、グローバルチャット機能
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Set

# ログ設定
channel_logger = logging.getLogger('channel')

class ChannelManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chinese_conversion_map = self._create_chinese_map()
        
    def _create_chinese_map(self) -> Dict[str, str]:
        """えせ中国語変換マップを作成"""
        return {
            'あ': '阿', 'い': '伊', 'う': '宇', 'え': '江', 'お': '於',
            'か': '加', 'き': '基', 'く': '久', 'け': '計', 'こ': '古',
            'が': '雅', 'ぎ': '義', 'ぐ': '具', 'げ': '下', 'ご': '語',
            'さ': '佐', 'し': '師', 'す': '須', 'せ': '世', 'そ': '曽',
            'ざ': '座', 'じ': '次', 'ず': '図', 'ぜ': '是', 'ぞ': '造',
            'た': '太', 'ち': '地', 'つ': '津', 'て': '天', 'と': '都',
            'だ': '打', 'ぢ': '遅', 'づ': '豆', 'で': '出', 'ど': '度',
            'な': '奈', 'に': '二', 'ぬ': '奴', 'ね': '根', 'の': '野',
            'は': '波', 'ひ': '比', 'ふ': '風', 'へ': '変', 'ほ': '保',
            'ば': '馬', 'び': '美', 'ぶ': '武', 'べ': '部', 'ぼ': '母',
            'ぱ': '巴', 'ぴ': '皮', 'ぷ': '普', 'ぺ': '辺', 'ぽ': '歩',
            'ま': '真', 'み': '美', 'む': '無', 'め': '女', 'も': '母',
            'や': '也', 'ゆ': '由', 'よ': '与',
            'ら': '良', 'り': '利', 'る': '流', 'れ': '礼', 'ろ': '路',
            'わ': '和', 'ゐ': '井', 'ゑ': '恵', 'を': '乎', 'ん': '无',
            'ー': '―', 'ッ': '津', 'ャ': '也', 'ュ': '由', 'ョ': '与'
        }

    def convert_to_chinese(self, text: str) -> str:
        """テキストをえせ中国語に変換"""
        try:
            result = ""
            for char in text:
                if char in self.chinese_conversion_map:
                    result += self.chinese_conversion_map[char]
                else:
                    result += char
            return result
        except Exception as e:
            channel_logger.error(f"えせ中国語変換エラー: {e}")
            return text

    @app_commands.command(name="setlogchannel", description="ログ出力チャンネルを設定します（管理者限定）")
    @app_commands.describe(channel="ログを出力するチャンネル")
    async def setlogchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """ログチャンネルを設定"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return

        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # データベースに保存
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO guild_settings 
                    (guild_id, log_channel_id) VALUES (?, ?)
                ''', (interaction.guild.id, channel.id))
                await db.commit()

            embed = discord.Embed(
                title="📝 ログチャンネル設定",
                description=f"ログチャンネルを {channel.mention} に設定しました。",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            channel_logger.error(f"ログチャンネル設定エラー: {e}")
            await interaction.response.send_message("❌ ログチャンネルの設定に失敗しました。", ephemeral=True)

    @app_commands.command(name="setchinesechannel", description="えせ中国語専用チャンネルを設定します（管理者限定）")
    @app_commands.describe(channel="えせ中国語専用にするチャンネル")
    async def setchinesechannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """えせ中国語専用チャンネルを設定"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return

        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # データベースに保存
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO guild_settings 
                    (guild_id, chinese_channel_id) VALUES (?, ?)
                ''', (interaction.guild.id, channel.id))
                await db.commit()

            embed = discord.Embed(
                title="🇨🇳 えせ中国語チャンネル設定",
                description=f"{channel.mention} をえせ中国語専用チャンネルに設定しました。",
                color=0xff0000,
                timestamp=datetime.now()
            )
            embed.add_field(
                name="使用方法",
                value="このチャンネルでは、メッセージが自動でえせ中国語に変換されます。",
                inline=False
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            channel_logger.error(f"えせ中国語チャンネル設定エラー: {e}")
            await interaction.response.send_message("❌ えせ中国語チャンネルの設定に失敗しました。", ephemeral=True)

    @app_commands.command(name="removechinesechannel", description="えせ中国語専用チャンネル設定を解除します（管理者限定）")
    async def removechinesechannel(self, interaction: discord.Interaction):
        """えせ中国語専用チャンネル設定を解除"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return

        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # データベースから削除
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    UPDATE guild_settings 
                    SET chinese_channel_id = NULL 
                    WHERE guild_id = ?
                ''', (interaction.guild.id,))
                await db.commit()

            embed = discord.Embed(
                title="🇨🇳 えせ中国語チャンネル解除",
                description="えせ中国語専用チャンネル設定を解除しました。",
                color=0xff9900,
                timestamp=datetime.now()
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            channel_logger.error(f"えせ中国語チャンネル解除エラー: {e}")
            await interaction.response.send_message("❌ えせ中国語チャンネルの解除に失敗しました。", ephemeral=True)

    @app_commands.command(name="lockchinesechannels", description="えせ中国語専用チャンネルをロックします（管理者限定）")
    async def lockchinesechannels(self, interaction: discord.Interaction):
        """えせ中国語専用チャンネルをロック"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return

        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # データベースに保存
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO guild_settings 
                    (guild_id, chinese_locked) VALUES (?, ?)
                ''', (interaction.guild.id, True))
                await db.commit()

            embed = discord.Embed(
                title="🔒 えせ中国語チャンネルロック",
                description="えせ中国語専用チャンネルをロックしました。",
                color=0xff0000,
                timestamp=datetime.now()
            )
            embed.add_field(
                name="効果",
                value="えせ中国語チャンネルでの違反メッセージが削除されるようになります。",
                inline=False
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            channel_logger.error(f"えせ中国語チャンネルロックエラー: {e}")
            await interaction.response.send_message("❌ えせ中国語チャンネルのロックに失敗しました。", ephemeral=True)

    @app_commands.command(name="unlockchinesechannels", description="えせ中国語専用チャンネルのロックを解除します（管理者限定）")
    async def unlockchinesechannels(self, interaction: discord.Interaction):
        """えせ中国語専用チャンネルのロックを解除"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return

        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # データベースを更新
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    UPDATE guild_settings 
                    SET chinese_locked = ? 
                    WHERE guild_id = ?
                ''', (False, interaction.guild.id))
                await db.commit()

            embed = discord.Embed(
                title="🔓 えせ中国語チャンネルロック解除",
                description="えせ中国語専用チャンネルのロックを解除しました。",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            channel_logger.error(f"えせ中国語チャンネルロック解除エラー: {e}")
            await interaction.response.send_message("❌ えせ中国語チャンネルのロック解除に失敗しました。", ephemeral=True)

    @app_commands.command(name="setglobalchat", description="えせ中国語グローバルチャットチャンネルを設定します（管理者限定）")
    @app_commands.describe(channel="グローバルチャットに使用するチャンネル")
    async def setglobalchat(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """グローバルチャットチャンネルを設定"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return

        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # データベースに保存
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO guild_settings 
                    (guild_id, global_chat_channel_id) VALUES (?, ?)
                ''', (interaction.guild.id, channel.id))
                await db.commit()

            embed = discord.Embed(
                title="🌐 グローバルチャット設定",
                description=f"{channel.mention} をグローバルチャットに設定しました。",
                color=0x0099ff,
                timestamp=datetime.now()
            )
            embed.add_field(
                name="機能",
                value="このチャンネルのメッセージが他のサーバーのグローバルチャットと共有されます。",
                inline=False
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            channel_logger.error(f"グローバルチャット設定エラー: {e}")
            await interaction.response.send_message("❌ グローバルチャットの設定に失敗しました。", ephemeral=True)

    @app_commands.command(name="removeglobalchat", description="えせ中国語グローバルチャット設定を解除します（管理者限定）")
    async def removeglobalchat(self, interaction: discord.Interaction):
        """グローバルチャット設定を解除"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return

        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # データベースから削除
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    UPDATE guild_settings 
                    SET global_chat_channel_id = NULL 
                    WHERE guild_id = ?
                ''', (interaction.guild.id,))
                await db.commit()

            embed = discord.Embed(
                title="🌐 グローバルチャット解除",
                description="グローバルチャット設定を解除しました。",
                color=0xff9900,
                timestamp=datetime.now()
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            channel_logger.error(f"グローバルチャット解除エラー: {e}")
            await interaction.response.send_message("❌ グローバルチャットの解除に失敗しました。", ephemeral=True)

    @app_commands.command(name="checkviolations", description="違反回数を確認します")
    @app_commands.describe(member="確認するメンバー（省略すると自分）")
    async def checkviolations(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        """違反回数を確認"""
        try:
            target_member = member or interaction.user
            
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # データベースから違反回数を取得
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT violation_count FROM user_violations 
                    WHERE guild_id = ? AND user_id = ?
                ''', (interaction.guild.id, target_member.id))
                result = await cursor.fetchone()
                violation_count = result[0] if result else 0

            embed = discord.Embed(
                title="⚠️ 違反回数確認",
                color=0xff9900 if violation_count > 0 else 0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url=target_member.display_avatar.url)
            embed.add_field(name="ユーザー", value=target_member.mention, inline=True)
            embed.add_field(name="違反回数", value=f"{violation_count}回", inline=True)

            if violation_count >= 3:
                embed.add_field(name="状態", value="⚠️ 警告レベル", inline=True)
            else:
                embed.add_field(name="状態", value="✅ 正常", inline=True)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            channel_logger.error(f"違反回数確認エラー: {e}")
            await interaction.response.send_message("❌ 違反回数の確認に失敗しました。", ephemeral=True)

    @app_commands.command(name="resetviolations", description="違反回数をリセットします（管理者限定）")
    @app_commands.describe(member="リセットするメンバー")
    async def resetviolations(self, interaction: discord.Interaction, member: discord.Member):
        """違反回数をリセット"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return

        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # データベースから違反回数をリセット
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    DELETE FROM user_violations 
                    WHERE guild_id = ? AND user_id = ?
                ''', (interaction.guild.id, member.id))
                await db.commit()

            embed = discord.Embed(
                title="🔄 違反回数リセット",
                description=f"{member.mention} の違反回数をリセットしました。",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            channel_logger.error(f"違反回数リセットエラー: {e}")
            await interaction.response.send_message("❌ 違反回数のリセットに失敗しました。", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        """メッセージイベント処理"""
        if message.author.bot:
            return

        try:
            # えせ中国語チャンネル処理
            await self._handle_chinese_channel(message)
            
            # グローバルチャット処理
            await self._handle_global_chat(message)
            
        except Exception as e:
            channel_logger.error(f"メッセージ処理エラー: {e}")

    async def _handle_chinese_channel(self, message):
        """えせ中国語チャンネル処理"""
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                return

            # 設定を取得
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT chinese_channel_id, chinese_locked 
                    FROM guild_settings WHERE guild_id = ?
                ''', (message.guild.id,))
                result = await cursor.fetchone()
                
                if not result or not result[0]:
                    return
                
                chinese_channel_id, is_locked = result
                
                if message.channel.id != chinese_channel_id:
                    return

                # えせ中国語に変換
                converted_text = self.convert_to_chinese(message.content)
                
                if converted_text != message.content:
                    # メッセージを削除して変換版を送信
                    await message.delete()
                    
                    embed = discord.Embed(
                        description=converted_text,
                        color=message.author.color or 0x99aab5,
                        timestamp=datetime.now()
                    )
                    embed.set_author(
                        name=message.author.display_name,
                        icon_url=message.author.display_avatar.url
                    )
                    
                    await message.channel.send(embed=embed)

        except Exception as e:
            channel_logger.error(f"えせ中国語処理エラー: {e}")

    async def _handle_global_chat(self, message):
        """グローバルチャット処理"""
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                return

            # 現在のチャンネルがグローバルチャットかチェック
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT guild_id FROM guild_settings 
                    WHERE global_chat_channel_id = ?
                ''', (message.channel.id,))
                result = await cursor.fetchone()
                
                if not result:
                    return

                # 他のグローバルチャットチャンネルを取得
                cursor = await db.execute('''
                    SELECT guild_id, global_chat_channel_id 
                    FROM guild_settings 
                    WHERE global_chat_channel_id IS NOT NULL 
                    AND guild_id != ?
                ''', (message.guild.id,))
                other_channels = await cursor.fetchall()

                # 他のチャンネルにメッセージを転送
                for guild_id, channel_id in other_channels:
                    try:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            embed = discord.Embed(
                                description=message.content,
                                color=message.author.color or 0x99aab5,
                                timestamp=datetime.now()
                            )
                            embed.set_author(
                                name=f"{message.author.display_name} ({message.guild.name})",
                                icon_url=message.author.display_avatar.url
                            )
                            embed.set_footer(text="グローバルチャット")
                            
                            await channel.send(embed=embed)
                    except:
                        pass  # エラーは無視

        except Exception as e:
            channel_logger.error(f"グローバルチャット処理エラー: {e}")

async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(ChannelManagementCog(bot))