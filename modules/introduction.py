"""
RTKS Discord Bot - 自己紹介システムモジュール
ボイスチャンネル参加時の自動自己紹介表示機能
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from typing import Optional

# ログ設定
intro_logger = logging.getLogger('introduction')

class IntroductionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_intro", description="自己紹介システムをセットアップします（管理者限定）")
    @app_commands.describe(
        intro_channel="自己紹介を表示するチャンネル",
        secret_role="除外するロール名（このロールのユーザーは表示されません）"
    )
    async def setup_intro(self, interaction: discord.Interaction, intro_channel: discord.TextChannel, secret_role: str = "秘密のロール"):
        """自己紹介システムをセットアップ"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return
        
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return
            
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO intro_settings 
                    (guild_id, intro_channel_id, secret_role_name, is_enabled)
                    VALUES (?, ?, ?, 1)
                ''', (interaction.guild.id, intro_channel.id, secret_role))
                await db.commit()
            
            embed = discord.Embed(
                title="🎭 自己紹介システム設定完了",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.add_field(name="自己紹介チャンネル", value=intro_channel.mention, inline=False)
            embed.add_field(name="除外ロール", value=secret_role, inline=False)
            embed.add_field(
                name="使い方", 
                value="ユーザーがボイスチャンネルに参加すると、自動で自己紹介が表示されます。",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            intro_logger.error(f"自己紹介システム設定エラー: {e}")
            await interaction.response.send_message("❌ 自己紹介システムの設定中にエラーが発生しました。", ephemeral=True)

    @app_commands.command(name="intro_toggle", description="自己紹介システムのオン/オフを切り替えます（管理者限定）")
    async def intro_toggle(self, interaction: discord.Interaction):
        """自己紹介システムのオン/オフを切り替え"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return
        
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return
            
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                # 現在の状態を取得
                cursor = await db.execute('''
                    SELECT is_enabled FROM intro_settings WHERE guild_id = ?
                ''', (interaction.guild.id,))
                result = await cursor.fetchone()
                
                if not result:
                    await interaction.response.send_message("❌ 自己紹介システムが設定されていません。先に `/setup_intro` を実行してください。", ephemeral=True)
                    return
                
                # 状態を切り替え
                new_status = not result[0]
                await db.execute('''
                    UPDATE intro_settings SET is_enabled = ? WHERE guild_id = ?
                ''', (new_status, interaction.guild.id))
                await db.commit()
            
            status_text = "有効" if new_status else "無効"
            embed = discord.Embed(
                title="🎭 自己紹介システム設定変更",
                color=0x00ff00 if new_status else 0xff9900,
                timestamp=datetime.now()
            )
            embed.add_field(name="状態", value=f"自己紹介システムを **{status_text}** にしました", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            intro_logger.error(f"自己紹介システム切り替えエラー: {e}")
            await interaction.response.send_message("❌ 設定変更中にエラーが発生しました。", ephemeral=True)

    @app_commands.command(name="set_my_intro", description="自分の自己紹介を直接設定します")
    @app_commands.describe(introduction="自己紹介文（1000文字以内）")
    async def set_my_intro(self, interaction: discord.Interaction, introduction: str):
        """自分の自己紹介を設定"""
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return
            
            if len(introduction) > 1000:
                await interaction.response.send_message("❌ 自己紹介は1000文字以内で入力してください。", ephemeral=True)
                return
            
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                # 自己紹介システムが有効かチェック
                cursor = await db.execute('''
                    SELECT intro_channel_id FROM intro_settings 
                    WHERE guild_id = ? AND is_enabled = 1
                ''', (interaction.guild.id,))
                setting = await cursor.fetchone()
                
                if not setting:
                    await interaction.response.send_message("❌ 自己紹介システムが有効ではありません。", ephemeral=True)
                    return
                
                # データベースに保存
                await db.execute('''
                    INSERT OR REPLACE INTO user_introductions 
                    (guild_id, user_id, introduction_text, intro_channel_id)
                    VALUES (?, ?, ?, ?)
                ''', (interaction.guild.id, interaction.user.id, introduction, setting[0]))
                await db.commit()
            
            embed = discord.Embed(
                title="🎭 自己紹介設定完了",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.add_field(name="設定した自己紹介", value=introduction[:500] + ("..." if len(introduction) > 500 else ""), inline=False)
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            intro_logger.error(f"自己紹介設定エラー: {e}")
            await interaction.response.send_message("❌ 自己紹介の設定中にエラーが発生しました。", ephemeral=True)

    @app_commands.command(name="intro_status", description="自己紹介システムの設定状況を確認します")
    async def intro_status(self, interaction: discord.Interaction):
        """自己紹介システムの設定状況を確認"""
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return
            
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT intro_channel_id, secret_role_name, is_enabled 
                    FROM intro_settings WHERE guild_id = ?
                ''', (interaction.guild.id,))
                setting = await cursor.fetchone()
                
                if not setting:
                    await interaction.response.send_message("❌ 自己紹介システムが設定されていません。", ephemeral=True)
                    return
                
                intro_channel_id, secret_role_name, is_enabled = setting
                intro_channel = self.bot.get_channel(intro_channel_id)
                
                # 登録済み自己紹介数を取得
                cursor = await db.execute('''
                    SELECT COUNT(*) FROM user_introductions WHERE guild_id = ?
                ''', (interaction.guild.id,))
                intro_count = (await cursor.fetchone())[0]
            
            embed = discord.Embed(
                title="🎭 自己紹介システム状況",
                color=0x00ff00 if is_enabled else 0xff9900,
                timestamp=datetime.now()
            )
            embed.add_field(name="状態", value="有効" if is_enabled else "無効", inline=True)
            embed.add_field(name="自己紹介チャンネル", value=intro_channel.mention if intro_channel else "チャンネルが見つかりません", inline=True)
            embed.add_field(name="除外ロール", value=secret_role_name, inline=True)
            embed.add_field(name="登録済み自己紹介", value=f"{intro_count}件", inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            intro_logger.error(f"自己紹介システム状況確認エラー: {e}")
            await interaction.response.send_message("❌ 状況確認中にエラーが発生しました。", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """ボイスチャンネル参加/退出時の処理"""
        try:
            if member.bot:
                return

            # ボイスチャンネルに参加した場合
            if before.channel is None and after.channel is not None:
                await self._handle_voice_join(member, after.channel)
            
            # ボイスチャンネルから退出した場合
            elif before.channel is not None and after.channel is None:
                await self._handle_voice_leave(member, before.channel)

        except Exception as e:
            intro_logger.error(f"ボイス状態更新処理エラー: {e}")

    async def _handle_voice_join(self, member, channel):
        """ボイスチャンネル参加時の処理"""
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                return

            guild = member.guild
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                # 自己紹介システム設定を取得
                cursor = await db.execute('''
                    SELECT intro_channel_id, secret_role_name, is_enabled 
                    FROM intro_settings WHERE guild_id = ?
                ''', (guild.id,))
                setting = await cursor.fetchone()
                
                if not setting or not setting[2]:  # システムが無効
                    return
                
                intro_channel_id, secret_role_name, _ = setting
                intro_channel = self.bot.get_channel(intro_channel_id)
                
                if not intro_channel:
                    return

                # 除外ロールをチェック
                if discord.utils.get(member.roles, name=secret_role_name):
                    return

                # 自己紹介を取得
                introduction = await self._fetch_introduction(member, guild.id)
                if introduction:
                    await self._send_introduction_embed(intro_channel, member, channel, introduction, "参加")

        except Exception as e:
            intro_logger.error(f"ボイス参加処理エラー: {e}")

    async def _handle_voice_leave(self, member, channel):
        """ボイスチャンネル退出時の処理"""
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                return

            guild = member.guild
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                # 自己紹介システム設定を取得
                cursor = await db.execute('''
                    SELECT intro_channel_id, secret_role_name, is_enabled 
                    FROM intro_settings WHERE guild_id = ?
                ''', (guild.id,))
                setting = await cursor.fetchone()
                
                if not setting or not setting[2]:  # システムが無効
                    return
                
                intro_channel_id, secret_role_name, _ = setting
                intro_channel = self.bot.get_channel(intro_channel_id)
                
                if not intro_channel:
                    return

                # 除外ロールをチェック
                if discord.utils.get(member.roles, name=secret_role_name):
                    return

                # 自己紹介を取得
                introduction = await self._fetch_introduction(member, guild.id)
                if introduction:
                    await self._send_introduction_embed(intro_channel, member, channel, introduction, "退出")

        except Exception as e:
            intro_logger.error(f"ボイス退出処理エラー: {e}")

    async def _fetch_introduction(self, member, guild_id):
        """データベースから自己紹介を取得"""
        try:
            from database import db_manager
            import aiosqlite
            
            async with aiosqlite.connect(db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT introduction_text FROM user_introductions 
                    WHERE guild_id = ? AND user_id = ?
                ''', (guild_id, member.id))
                result = await cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            intro_logger.error(f"自己紹介取得エラー: {e}")
            return None

    async def _send_introduction_embed(self, channel, member, voice_channel, introduction, action):
        """自己紹介埋め込みメッセージを送信"""
        try:
            color = 0x00ff00 if action == "参加" else 0xff9900
            title = f"🎭 {member.display_name} さんがボイスチャンネルに{action}しました"
            
            embed = discord.Embed(
                title=title,
                color=color,
                timestamp=datetime.now()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(
                name="チャンネル",
                value=f"🔊 {voice_channel.name}",
                inline=True
            )
            embed.add_field(
                name="自己紹介",
                value=introduction[:1000],  # 制限
                inline=False
            )
            
            # 削除予告
            embed.set_footer(text="このメッセージは5分後に自動削除されます")
            
            message = await channel.send(embed=embed)
            
            # 5分後に自動削除
            import asyncio
            await asyncio.sleep(300)  # 5分 = 300秒
            try:
                await message.delete()
            except:
                pass  # メッセージが既に削除されている場合は無視
                
        except Exception as e:
            intro_logger.error(f"自己紹介埋め込み送信エラー: {e}")

async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(IntroductionCog(bot))