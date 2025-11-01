"""
RTKS Discord Bot - ロール管理モジュール
ロールパネル、ロール情報、一括ロール操作機能
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from typing import List, Optional

# ログ設定
roles_logger = logging.getLogger('roles')

class RoleView(discord.ui.View):
    def __init__(self, roles: List[discord.Role]):
        super().__init__(timeout=None)
        self.roles = roles
        
        # 最大25個のボタンを作成（Discordの制限）
        for i, role in enumerate(roles[:25]):
            button = RoleButton(role, i)
            self.add_item(button)

class RoleButton(discord.ui.Button):
    def __init__(self, role: discord.Role, index: int):
        super().__init__(
            label=role.name,
            style=discord.ButtonStyle.secondary,
            emoji="🎭",
            custom_id=f"role_{role.id}_{index}"
        )
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        try:
            member = interaction.guild.get_member(interaction.user.id)
            if not member:
                await interaction.response.send_message("❌ メンバー情報を取得できませんでした。", ephemeral=True)
                return

            if self.role in member.roles:
                await member.remove_roles(self.role)
                await interaction.response.send_message(
                    f"➖ {self.role.mention} ロールを削除しました。",
                    ephemeral=True
                )
            else:
                await member.add_roles(self.role)
                await interaction.response.send_message(
                    f"➕ {self.role.mention} ロールを付与しました。",
                    ephemeral=True
                )

        except discord.Forbidden:
            await interaction.response.send_message("❌ ロールの操作権限がありません。", ephemeral=True)
        except Exception as e:
            roles_logger.error(f"ロール操作エラー: {e}")
            await interaction.response.send_message("❌ ロール操作中にエラーが発生しました。", ephemeral=True)

class RolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="createrolepanel", description="ロールパネルを作成します（管理者限定）")
    @app_commands.describe(
        title="パネルのタイトル",
        description="パネルの説明",
        roles="ロール名をカンマ区切りで指定"
    )
    async def createrolepanel(self, interaction: discord.Interaction, title: str, description: str, roles: str):
        """ロールパネルを作成"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return

        try:
            # ロール名を解析
            role_names = [name.strip() for name in roles.split(',')]
            role_objects = []
            
            for role_name in role_names:
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if role:
                    role_objects.append(role)
                else:
                    await interaction.response.send_message(f"❌ ロール '{role_name}' が見つかりません。", ephemeral=True)
                    return

            if not role_objects:
                await interaction.response.send_message("❌ 有効なロールが指定されていません。", ephemeral=True)
                return

            if len(role_objects) > 25:
                await interaction.response.send_message("❌ ロールは最大25個まで指定できます。", ephemeral=True)
                return

            # 埋め込みメッセージを作成
            embed = discord.Embed(
                title=f"🎭 {title}",
                description=description,
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            role_list = "\n".join([f"• {role.mention}" for role in role_objects])
            embed.add_field(name="利用可能なロール", value=role_list, inline=False)
            embed.set_footer(text="ボタンをクリックしてロールを取得/削除できます")

            # ロールビューを作成
            view = RoleView(role_objects)
            await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            roles_logger.error(f"ロールパネル作成エラー: {e}")
            await interaction.response.send_message("❌ ロールパネルの作成に失敗しました。", ephemeral=True)

    @app_commands.command(name="listroles", description="サーバーのロール一覧を表示します")
    async def listroles(self, interaction: discord.Interaction):
        """サーバーのロール一覧を表示"""
        try:
            roles = [role for role in interaction.guild.roles if role.name != "@everyone"]
            roles.sort(key=lambda r: r.position, reverse=True)

            if not roles:
                await interaction.response.send_message("❌ サーバーにロールがありません。", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"🎭 {interaction.guild.name} のロール一覧",
                color=0x00ff00,
                timestamp=datetime.now()
            )

            # ロールを20個ずつ分割して表示
            for i in range(0, len(roles), 20):
                role_chunk = roles[i:i+20]
                role_list = []
                
                for role in role_chunk:
                    member_count = len(role.members)
                    color_hex = f"#{role.color.value:06x}" if role.color.value else "#000000"
                    role_list.append(f"• {role.mention} ({member_count}人) `{color_hex}`")

                field_name = f"ロール ({i+1}-{min(i+20, len(roles))})"
                embed.add_field(name=field_name, value="\n".join(role_list), inline=False)

            embed.add_field(
                name="使い方",
                value="ロールパネルを作成するには:\n`/createrolepanel title:タイトル description:説明 roles:ロール名1,ロール名2`",
                inline=False
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            roles_logger.error(f"ロール一覧表示エラー: {e}")
            await interaction.response.send_message("❌ ロール一覧の取得に失敗しました。", ephemeral=True)

    @app_commands.command(name="roleinfo", description="指定したロールの詳細情報を表示します")
    @app_commands.describe(role="情報を表示するロール")
    async def roleinfo(self, interaction: discord.Interaction, role: discord.Role):
        """ロールの詳細情報を表示"""
        try:
            embed = discord.Embed(
                title=f"🎭 ロール情報: {role.name}",
                color=role.color or 0x99aab5,
                timestamp=datetime.now()
            )

            # 基本情報
            embed.add_field(name="ID", value=role.id, inline=True)
            embed.add_field(name="作成日", value=role.created_at.strftime("%Y/%m/%d %H:%M"), inline=True)
            embed.add_field(name="ポジション", value=role.position, inline=True)
            
            # カラー情報
            color_hex = f"#{role.color.value:06x}" if role.color.value else "#000000"
            embed.add_field(name="カラー", value=color_hex, inline=True)
            embed.add_field(name="メンション可能", value="✅" if role.mentionable else "❌", inline=True)
            embed.add_field(name="個別表示", value="✅" if role.hoist else "❌", inline=True)

            # メンバー数
            member_count = len(role.members)
            embed.add_field(name="メンバー数", value=f"{member_count}人", inline=True)

            # 権限情報
            permissions = []
            if role.permissions.administrator:
                permissions.append("👑 管理者")
            if role.permissions.manage_guild:
                permissions.append("⚙️ サーバー管理")
            if role.permissions.manage_roles:
                permissions.append("🎭 ロール管理")
            if role.permissions.manage_channels:
                permissions.append("📝 チャンネル管理")
            if role.permissions.kick_members:
                permissions.append("👢 メンバーキック")
            if role.permissions.ban_members:
                permissions.append("🔨 メンバーBAN")

            if permissions:
                embed.add_field(name="主要権限", value="\n".join(permissions[:10]), inline=False)

            # メンバーサンプル（最大10人）
            if role.members:
                member_sample = [member.display_name for member in role.members[:10]]
                if len(role.members) > 10:
                    member_sample.append(f"他{len(role.members) - 10}人...")
                embed.add_field(name="メンバー", value="\n".join(member_sample), inline=False)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            roles_logger.error(f"ロール情報表示エラー: {e}")
            await interaction.response.send_message("❌ ロール情報の取得に失敗しました。", ephemeral=True)

    @app_commands.command(name="rolestat", description="サーバーのロール統計を表示します")
    async def rolestat(self, interaction: discord.Interaction):
        """サーバーのロール統計を表示"""
        try:
            roles = [role for role in interaction.guild.roles if role.name != "@everyone"]
            
            embed = discord.Embed(
                title=f"📊 {interaction.guild.name} のロール統計",
                color=0x00ff00,
                timestamp=datetime.now()
            )

            # 基本統計
            embed.add_field(name="総ロール数", value=f"{len(roles)}個", inline=True)
            
            # メンバー数によるソート
            roles_with_members = [role for role in roles if len(role.members) > 0]
            roles_without_members = [role for role in roles if len(role.members) == 0]
            
            embed.add_field(name="使用中のロール", value=f"{len(roles_with_members)}個", inline=True)
            embed.add_field(name="未使用のロール", value=f"{len(roles_without_members)}個", inline=True)

            # 最も人気のロール（上位5個）
            if roles_with_members:
                popular_roles = sorted(roles_with_members, key=lambda r: len(r.members), reverse=True)[:5]
                popular_list = []
                for i, role in enumerate(popular_roles, 1):
                    popular_list.append(f"{i}. {role.mention} ({len(role.members)}人)")
                embed.add_field(name="人気ロール TOP5", value="\n".join(popular_list), inline=False)

            # 権限を持つロール
            admin_roles = [role for role in roles if role.permissions.administrator]
            manage_roles = [role for role in roles if role.permissions.manage_guild]
            
            embed.add_field(name="管理者権限", value=f"{len(admin_roles)}個", inline=True)
            embed.add_field(name="サーバー管理権限", value=f"{len(manage_roles)}個", inline=True)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            roles_logger.error(f"ロール統計表示エラー: {e}")
            await interaction.response.send_message("❌ ロール統計の取得に失敗しました。", ephemeral=True)

    @app_commands.command(name="memberroles", description="指定したメンバーの所有ロールを表示します")
    @app_commands.describe(member="ロールを確認するメンバー")
    async def memberroles(self, interaction: discord.Interaction, member: discord.Member):
        """メンバーの所有ロールを表示"""
        try:
            roles = [role for role in member.roles if role.name != "@everyone"]
            roles.sort(key=lambda r: r.position, reverse=True)

            embed = discord.Embed(
                title=f"🎭 {member.display_name} のロール",
                color=member.color or 0x99aab5,
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)

            if not roles:
                embed.description = "このメンバーは特別なロールを持っていません。"
            else:
                role_list = []
                for role in roles:
                    color_hex = f"#{role.color.value:06x}" if role.color.value else "#000000"
                    role_list.append(f"• {role.mention} `{color_hex}`")

                embed.add_field(name=f"ロール ({len(roles)}個)", value="\n".join(role_list), inline=False)

                # 権限サマリー
                permissions = []
                if any(role.permissions.administrator for role in roles):
                    permissions.append("👑 管理者")
                if any(role.permissions.manage_guild for role in roles):
                    permissions.append("⚙️ サーバー管理")
                if any(role.permissions.manage_roles for role in roles):
                    permissions.append("🎭 ロール管理")
                if any(role.permissions.manage_channels for role in roles):
                    permissions.append("📝 チャンネル管理")

                if permissions:
                    embed.add_field(name="主要権限", value=" ".join(permissions), inline=False)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            roles_logger.error(f"メンバーロール表示エラー: {e}")
            await interaction.response.send_message("❌ メンバーロール情報の取得に失敗しました。", ephemeral=True)

    @app_commands.command(name="bulkrole", description="複数のメンバーに一括でロールを付与/削除します（管理者限定）")
    @app_commands.describe(
        action="実行する操作（add/remove）",
        role="対象のロール",
        members="メンバーをカンマ区切りで指定（ID、メンション、名前）"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="付与", value="add"),
        app_commands.Choice(name="削除", value="remove")
    ])
    async def bulkrole(self, interaction: discord.Interaction, action: str, role: discord.Role, members: str):
        """複数メンバーに一括でロール操作"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者のみが使用できます。", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            # メンバーを解析
            member_identifiers = [m.strip() for m in members.split(',')]
            target_members = []
            failed_members = []

            for identifier in member_identifiers:
                member = None
                
                # ID で検索
                if identifier.isdigit():
                    member = interaction.guild.get_member(int(identifier))
                
                # メンション形式 (<@!123456789>) で検索
                elif identifier.startswith('<@') and identifier.endswith('>'):
                    user_id = identifier.replace('<@!', '').replace('<@', '').replace('>', '')
                    if user_id.isdigit():
                        member = interaction.guild.get_member(int(user_id))
                
                # 名前で検索
                else:
                    member = discord.utils.get(interaction.guild.members, display_name=identifier)
                    if not member:
                        member = discord.utils.get(interaction.guild.members, name=identifier)

                if member:
                    target_members.append(member)
                else:
                    failed_members.append(identifier)

            if not target_members:
                await interaction.followup.send("❌ 有効なメンバーが見つかりませんでした。")
                return

            # ロール操作実行
            success_members = []
            error_members = []

            for member in target_members:
                try:
                    if action == "add":
                        if role not in member.roles:
                            await member.add_roles(role)
                            success_members.append(member.display_name)
                    elif action == "remove":
                        if role in member.roles:
                            await member.remove_roles(role)
                            success_members.append(member.display_name)
                except:
                    error_members.append(member.display_name)

            # 結果報告
            embed = discord.Embed(
                title="📊 一括ロール操作結果",
                color=0x00ff00 if not error_members else 0xff9900,
                timestamp=datetime.now()
            )

            action_text = "付与" if action == "add" else "削除"
            embed.add_field(name="対象ロール", value=role.mention, inline=False)
            embed.add_field(name="操作", value=action_text, inline=True)

            if success_members:
                embed.add_field(
                    name=f"✅ 成功 ({len(success_members)}人)",
                    value="\n".join(success_members[:10]) + (f"\n他{len(success_members)-10}人..." if len(success_members) > 10 else ""),
                    inline=False
                )

            if error_members:
                embed.add_field(
                    name=f"❌ 失敗 ({len(error_members)}人)",
                    value="\n".join(error_members[:5]) + (f"\n他{len(error_members)-5}人..." if len(error_members) > 5 else ""),
                    inline=False
                )

            if failed_members:
                embed.add_field(
                    name=f"❓ 見つからなかった ({len(failed_members)}人)",
                    value="\n".join(failed_members[:5]) + (f"\n他{len(failed_members)-5}人..." if len(failed_members) > 5 else ""),
                    inline=False
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            roles_logger.error(f"一括ロール操作エラー: {e}")
            await interaction.followup.send("❌ 一括ロール操作中にエラーが発生しました。")

async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(RolesCog(bot))