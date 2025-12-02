import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)

CATMEME_HTML_URL = "https://reitouko.site/catmeme_html/"
CATMEME_TRIGGERS = {
    # ...（元の辞書をそのまま）
    # 英語名のファイル
    "しばくぞ": "amoasuneko.html",
    "だる": "darucat.html",
    "ちぴ": "Dubidubiducat.html",
    "やった": "EDMcat.html",
    "やったー": "Girlfriend猫.html",
    "うるさい": "goat.html",
    "うま": "jyannkufoodneko.html",
    "かりかり": "kamikudakuneko.html",
    "www": "ramuneko.html",
    "nothappy": "Nothappy猫.html",
    "回転": "ooiia.html",
    "おつかい": "otukaineko.html",
    "パソコン": "PCcat.html",
    "pop": "popcat.html",
    "pura": "purapuracat.html",
    "suyaa": "suyaa.html",
    "syobon": "syobon.html",
    "waitingforlove": "WaitingForLovecat.html",
    
    # 日本語名のファイル
    "しばく": "しばくぞ.html",
    "ズッキー": "ズッキーニャ.html",
    "チベット": "チベットスナ猫.html",
    "トリガー": "トリガーハッピー猫.html",
    "ドライブ": "ドライブ猫.html",
    "ノリノリ": "ノリノリ猫.html",
    "ハァ": "ハァ？.html",
    "ハピハピ": "ハピハピ猫【これが一番好き】.html",
    "バイク1": "バイク猫１.html",
    "バイク2": "バイク猫２.html",
    "バッドトリップ": "バッドトリップ猫.html",
    "バナナ": "バナナ猫.html",
    "バナナダッシュ": "バナナ猫ダッシュ.html",
    "ヒートアップ": "ヒートアップ猫.html",
    "ヒーロー": "ヒーローインタビュー猫.html",
    "フクロウ12": "フクロウ猫１+２.html",
    "フクロウ1": "フクロウ猫１.html",
    "フクロウ2": "フクロウ猫２.html",
    "ホドモエ": "ホドモエシティ猫.html",
    "モフ叫び": "モフ猫叫び.html",
    "リンゴ": "リンゴ猫.html",
    "休日1": "休日お父さん猫１.html",
    "休日2": "休日お父さん猫２.html",
    "休日3": "休日お父さん猫３.html",
    "半径": "半径250㎝猫.html",
    "叱られる": "叱られる猫.html",
    "嘔吐1": "嘔吐猫１.html",
    "嘔吐2": "嘔吐猫２（猫単体）.html",
    "あくび": "大あくび猫.html"
}

CATMEME_ROLE_NAME = "catmeme"

class CatmemeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # in-memory caches
        self.enabled_guilds = set()
        self.role_ids = {}  # guild_id -> role_id
        # load persisted settings in background once bot is ready
        bot.loop.create_task(self._load_persisted_settings())

    async def _load_persisted_settings(self):
        await self.bot.wait_until_ready()
        # iterate over guilds the bot is in and load settings
        for guild in self.bot.guilds:
            settings = self.bot.db.load_guild_settings(str(guild.id)) if hasattr(self.bot, 'db') else {}
            cat_settings = settings.get('catmeme', {}) if settings else {}
            if cat_settings.get('enabled'):
                self.enabled_guilds.add(guild.id)
            if cat_settings.get('role_id'):
                try:
                    self.role_ids[guild.id] = int(cat_settings.get('role_id'))
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        # When joining a new guild, load its settings
        settings = self.bot.db.load_guild_settings(str(guild.id)) if hasattr(self.bot, 'db') else {}
        cat_settings = settings.get('catmeme', {}) if settings else {}
        if cat_settings.get('enabled'):
            self.enabled_guilds.add(guild.id)
        if cat_settings.get('role_id'):
            try:
                self.role_ids[guild.id] = int(cat_settings.get('role_id'))
            except Exception:
                pass

    async def _respond(self, interaction: discord.Interaction, content: str = None, *, embed: discord.Embed = None, ephemeral: bool = True):
        """Safely respond to an interaction, using response/send_message, followup, or channel fallback.
        This avoids Unknown interaction errors by checking response.is_done() and catching exceptions.
        """
        try:
            if not interaction.response.is_done():
                # send initial response
                await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)
                return
        except Exception:
            logger.warning('Failed to send initial response for interaction', exc_info=True)
        try:
            await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)
            return
        except Exception:
            logger.warning('Failed to send followup response for interaction', exc_info=True)
        # final fallback: send to channel if available
        try:
            if interaction.channel:
                await interaction.channel.send(content if content else embed and embed.to_dict())
        except Exception:
            logger.warning('Failed to send channel fallback message for interaction', exc_info=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # ギルドが有効化されていない場合は無視
        if message.guild.id not in self.enabled_guilds:
            return

        # catmemeロールを持っているか確認
        role_id = self.role_ids.get(message.guild.id)
        if role_id:
            has_role = any(role.id == role_id for role in message.author.roles)
        else:
            # fallback to checking by name
            has_role = any(role.name == CATMEME_ROLE_NAME for role in message.author.roles)
        if not has_role:
            return

        content = message.content.lower()
        for trigger, filename in CATMEME_TRIGGERS.items():
            if trigger.lower() in content:
                html_url = CATMEME_HTML_URL + filename
                await message.reply(html_url)
                break

    @app_commands.command(name="hannou", description="catmeme反応のオン・オフを切り替えます")
    @app_commands.describe(mode="on または off を指定してください")
    async def hannou(self, interaction: discord.Interaction, mode: str):
        if not interaction.guild:
            await interaction.response.send_message("このコマンドはサーバー内で使ってね！", ephemeral=True)
            return

        # For administrators: allow enabling/disabling for the entire guild (create role if needed)
        is_admin = bool(interaction.user.guild_permissions.administrator)

        mode = mode.lower()
        
        # 即時応答を送信
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        if mode == "on":
            if is_admin:
                # Admin: enable feature for the guild and create role if it doesn't exist
                self.enabled_guilds.add(interaction.guild.id)

                # catmemeロールがなければ作成
                role = discord.utils.get(interaction.guild.roles, name=CATMEME_ROLE_NAME)
                if not role:
                    try:
                        # ロール作成時に権限を明示的に設定
                        role = await interaction.guild.create_role(
                            name=CATMEME_ROLE_NAME,
                            permissions=discord.Permissions(
                                read_messages=True,
                                send_messages=True,
                                read_message_history=True
                            ),
                            reason="catmeme機能用ロール作成"
                        )
                        # ロールの位置を適切に設定（Botロールの下に）
                        bot_member = interaction.guild.get_member(self.bot.user.id)
                        if bot_member and bot_member.top_role:
                            await role.edit(position=bot_member.top_role.position - 1)
                    except discord.Forbidden:
                        await self._respond(interaction, "ロールを作成する権限がありません。")
                        return
                    except Exception as e:
                        await self._respond(interaction, f"ロール作成中にエラーが発生しました: {e}")
                        return

                # 実行者にロールを付与
                try:
                    await interaction.user.add_roles(role)
                except discord.Forbidden:
                    await self._respond(interaction, "ロールを付与する権限がありません。")
                    return

                # persist the guild settings
                if hasattr(self.bot, 'db'):
                    settings = self.bot.db.load_guild_settings(str(interaction.guild.id)) or {}
                    settings.setdefault('catmeme', {})
                    settings['catmeme']['enabled'] = True
                    settings['catmeme']['role_id'] = role.id
                    try:
                        self.bot.db.save_guild_settings(str(interaction.guild.id), settings)
                    except Exception:
                        pass
                # cache
                self.role_ids[interaction.guild.id] = role.id
                await self._respond(interaction, f"catmeme反応をオンにしました！ロール `{CATMEME_ROLE_NAME}` が利用可能です。")
            else:
                # Non-admins can opt-in (add role to themselves) only if the feature is enabled
                if interaction.guild.id not in self.enabled_guilds:
                    await self._respond(interaction, "このサーバーではcatmemeが無効になっています。管理者に `/hannou on` を実行してもらってください。")
                    return
                # Add role to user if role exists
                role = discord.utils.get(interaction.guild.roles, name=CATMEME_ROLE_NAME)
                if not role:
                    await self._respond(interaction, f"`{CATMEME_ROLE_NAME}` ロールが見つかりません。管理者に `/hannou on` を実行してもらってください。")
                    return
                try:
                    await interaction.user.add_roles(role)
                    # persist role id for this guild if not stored
                    if hasattr(self.bot, 'db'):
                        settings = self.bot.db.load_guild_settings(str(interaction.guild.id)) or {}
                        settings.setdefault('catmeme', {})
                        settings['catmeme']['role_id'] = role.id
                        try:
                            self.bot.db.save_guild_settings(str(interaction.guild.id), settings)
                        except Exception:
                            pass
                    self.role_ids[interaction.guild.id] = role.id
                    await self._respond(interaction, f"`{CATMEME_ROLE_NAME}` ロールを付与しました。反応を楽しんでください！")
                except discord.Forbidden:
                    await self._respond(interaction, "ロールを付与する権限がありません。サーバー管理者に依頼してください。")
                except Exception as e:
                    await self._respond(interaction, f"エラーが発生しました: {e}")

        elif mode == "off":
            if is_admin:
                self.enabled_guilds.discard(interaction.guild.id)
                # persist off setting
                if hasattr(self.bot, 'db'):
                    settings = self.bot.db.load_guild_settings(str(interaction.guild.id)) or {}
                    settings.setdefault('catmeme', {})
                    settings['catmeme']['enabled'] = False
                    # do not remove role id here; just disable
                    try:
                        self.bot.db.save_guild_settings(str(interaction.guild.id), settings)
                    except Exception:
                        pass
                await self._respond(interaction, "catmeme反応をオフにしました。")
            else:
                # Non-admins can opt-out by removing the role from themselves
                role = discord.utils.get(interaction.guild.roles, name=CATMEME_ROLE_NAME)
                if role and role in interaction.user.roles:
                    try:
                        await interaction.user.remove_roles(role)
                        await self._respond(interaction, "`catmeme` ロールを削除しました。")
                        return
                    except discord.Forbidden:
                        await self._respond(interaction, "ロールを削除する権限がありません。サーバー管理者に依頼してください。")
                    except Exception as e:
                        await self._respond(interaction, f"エラーが発生しました: {e}")
                        return
                await self._respond(interaction, "あなたは `catmeme` ロールを持っていないようです。")
            # (persist off already handled above for admins)
        else:
            await self._respond(interaction, "`on` か `off` を指定してね！")

    # Debug command removed to keep command set minimal

    # ロール付与用の新しいコマンドを追加
    @app_commands.command(name="catmeme_addrole", description="catmemeロールを自分に付与します")
    async def catmeme_addrole(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("このコマンドはサーバー内で使ってね！", ephemeral=True)
            return

        role = discord.utils.get(interaction.guild.roles, name=CATMEME_ROLE_NAME)
        if not role:
            await interaction.response.send_message(f"`{CATMEME_ROLE_NAME}` ロールが存在しません。まず `/hannou on` を実行してください。", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role)
            # persist role id for this guild (in case it was created externally)
            if hasattr(self.bot, 'db'):
                settings = self.bot.db.load_guild_settings(str(interaction.guild.id)) or {}
                settings.setdefault('catmeme', {})
                settings['catmeme']['role_id'] = role.id
                try:
                    self.bot.db.save_guild_settings(str(interaction.guild.id), settings)
                except Exception:
                    pass
            self.role_ids[interaction.guild.id] = role.id
            await interaction.response.send_message(f"`{CATMEME_ROLE_NAME}` ロールを付与しました！", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("ロールを付与する権限がありません。", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(CatmemeCog(bot))
