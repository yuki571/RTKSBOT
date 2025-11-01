"""
RTKS Discord Bot - 認証・メンション管理モジュール
認証パネル、メンション許可システム機能
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
from datetime import datetime
from typing import Optional

# ログ設定
auth_logger = logging.getLogger('auth')

class AuthView(discord.ui.View):
    def __init__(self, role: discord.Role, auth_url: str, delay: int = 20):
        super().__init__(timeout=None)
        self.role = role
        self.auth_url = auth_url
        self.delay = delay
        
    @discord.ui.button(label='認証を開始', style=discord.ButtonStyle.green, emoji='🔐')
    async def start_auth(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"🔐 認証を開始します。以下のURLにアクセスしてください:\n{self.auth_url}\n\n"
            f"⏰ {self.delay}秒後に自動でロールを付与します。",
            ephemeral=True
        )
        
        # 指定秒数後にロール付与
        await asyncio.sleep(self.delay)
        
        try:
            member = interaction.guild.get_member(interaction.user.id)
            if member and self.role not in member.roles:
                await member.add_roles(self.role)
                
                # フォローアップメッセージ
                try:
                    await interaction.followup.send(
                        f"✅ 認証が完了しました！ {self.role.mention} ロールを付与しました。",
                        ephemeral=True
                    )
                except:
                    pass  # フォローアップが失敗してもエラーにしない
                    
        except Exception as e:
            auth_logger.error(f"ロール付与エラー: {e}")

class PersistentAuthView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='認証', style=discord.ButtonStyle.green, emoji='🔐', custom_id='persistent_auth')
    async def persistent_auth(self, interaction: discord.Interaction, button: discord.ui.Button):
        # データベースから認証設定を取得する処理
        await interaction.response.send_message("🔐 認証機能は設定中です。", ephemeral=True)

class AuthCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="createpanel", description="認証パネルを作成します（管理者限定）")
    @app_commands.describe(
        role="付与するロール",
        auth_url="認証URL",
        delay="認証完了までの待機時間（秒）"
    )
    async def createpanel(self, interaction: discord.Interaction, role: discord.Role, auth_url: str, delay: int = 20):
        """認証パネルを作成"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔐 認証パネル",
            description=f"**{role.name}** ロールを取得するには、下のボタンをクリックして認証を完了してください。",
            color=role.color or 0x00ff00,
            timestamp=datetime.now()
        )
        embed.add_field(name="認証URL", value=f"[こちらをクリック]({auth_url})", inline=False)
        embed.add_field(name="待機時間", value=f"{delay}秒", inline=True)
        embed.set_footer(text="認証完了後、自動でロールが付与されます")

        view = AuthView(role, auth_url, delay)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="allowmention", description="自分をメンション許可リストに追加します")
    async def allowmention(self, interaction: discord.Interaction):
        """メンション許可リストに追加"""
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # データベースに追加
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO allowed_users (guild_id, user_id, username)
                    VALUES (?, ?, ?)
                ''', (interaction.guild.id, interaction.user.id, interaction.user.display_name))
                await db.commit()

            embed = discord.Embed(
                title="✅ メンション許可",
                description=f"{interaction.user.mention} をメンション許可リストに追加しました。",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            auth_logger.error(f"メンション許可追加エラー: {e}")
            await interaction.response.send_message("❌ メンション許可の追加に失敗しました。", ephemeral=True)

    @app_commands.command(name="addsuper", description="特別メンション権限を付与します（管理者限定）")
    @app_commands.describe(member="権限を付与するメンバー")
    async def addsuper(self, interaction: discord.Interaction, member: discord.Member):
        """特別メンション権限を付与"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return

        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # データベースに追加
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO super_users (guild_id, user_id, username)
                    VALUES (?, ?, ?)
                ''', (interaction.guild.id, member.id, member.display_name))
                await db.commit()

            embed = discord.Embed(
                title="👑 特別権限付与",
                description=f"{member.mention} に特別メンション権限を付与しました。",
                color=0xffd700,
                timestamp=datetime.now()
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            auth_logger.error(f"特別権限付与エラー: {e}")
            await interaction.response.send_message("❌ 特別権限の付与に失敗しました。", ephemeral=True)

    @app_commands.command(name="wakeup", description="指定ユーザーをメンションします（許可制）")
    @app_commands.describe(
        member="メンションするメンバー",
        count="メンション回数（1-10）",
        message="メッセージ"
    )
    async def wakeup(self, interaction: discord.Interaction, member: discord.Member, count: int = 1, message: str = ""):
        """許可されたユーザーをメンション"""
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # 権限チェック
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                # 特別権限チェック
                cursor = await db.execute('''
                    SELECT user_id FROM super_users 
                    WHERE guild_id = ? AND user_id = ?
                ''', (interaction.guild.id, interaction.user.id))
                is_super = await cursor.fetchone() is not None

                # 通常許可チェック
                cursor = await db.execute('''
                    SELECT user_id FROM allowed_users 
                    WHERE guild_id = ? AND user_id = ?
                ''', (interaction.guild.id, member.id))
                is_allowed = await cursor.fetchone() is not None

            if not is_super and not is_allowed:
                await interaction.response.send_message("❌ そのユーザーはメンション許可リストにありません。", ephemeral=True)
                return

            # 回数制限
            if count < 1 or count > 10:
                await interaction.response.send_message("❌ メンション回数は1-10回の範囲で指定してください。", ephemeral=True)
                return

            # メンション実行
            mention_text = " ".join([member.mention] * count)
            if message:
                mention_text += f"\n{message}"

            await interaction.response.send_message(mention_text)

        except Exception as e:
            auth_logger.error(f"メンション実行エラー: {e}")
            await interaction.response.send_message("❌ メンションの実行に失敗しました。", ephemeral=True)

async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(AuthCog(bot))
    
    # 永続化ビューを追加
    bot.add_view(PersistentAuthView())