import discord
from discord.ext import commands
from discord import app_commands, Interaction
import asyncio
from datetime import datetime
from typing import Dict, Optional, List
import json
import os

class BotMonitorCog(commands.Cog):
    """別のBOTのオンライン/オフライン状態を監視するCog（修正版）"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # monitored_bots: guild_id -> {target_id: info}
        self.monitored_bots: Dict[int, Dict[int, Dict]] = {}
        # per-guild online status: {guild_id: {bot_id: bool}}
        self.online_status: Dict[int, Dict[int, bool]] = {}
        # persisted_online_status stores the last-known persisted state from disk
        self.persisted_online_status: Dict[int, Dict[int, bool]] = {}
        # maintain a per-guild notification channel mapping for correct delivery
        self.notification_channel_id: Optional[int] = None
        self.notification_channel_ids: Dict[int, int] = {}
        self.monitoring_task: Optional[asyncio.Task] = None
        self.data_file = "monitored_bots.json"
        # monitoring interval in seconds (at least 60s as requested)
        self.CHECK_INTERVAL_SECONDS = 60
        
        self.load_data()
        print(f"✅ 監視Cog初期化完了: {len(self.monitored_bots)}体のBOTを監視中")
    
    async def cog_load(self):
        """Cogがロードされたときに実行"""
        print("🔧 Cogがロードされました")
        print(f"🔧 監視タスクを開始します... (既存タスク: {self.monitoring_task is not None})")
        self.monitoring_task = asyncio.create_task(self.start_monitoring())
        
    async def cog_unload(self):
        """Cogがアンロードされたときに実行"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        self.save_data()
    
    def load_data(self):
        """保存データを読み込む"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Try to load as per-guild mapping, otherwise attempt legacy format
                    raw = data.get('monitored_bots', {})
                    # detect whether raw is nested or flat
                    is_nested = False
                    if isinstance(raw, dict) and raw:
                        # if keys of raw are guild ids and values are dicts mapping to targets
                        first_val = next(iter(raw.values()))
                        if isinstance(first_val, dict):
                            is_nested = True
                    if is_nested:
                        self.monitored_bots = {int(gid): {int(tid): info for tid, info in targets.items()} for gid, targets in raw.items()}
                    else:
                        # legacy: global list of targets -> map them to guilds where the member exists
                        global_targets = {int(k): v for k, v in raw.items()}
                        for guild in self.bot.guilds:
                            gid = guild.id
                            for tid, info in global_targets.items():
                                member = guild.get_member(tid)
                                if member:
                                    self.monitored_bots.setdefault(gid, {})[tid] = info
                    # normalize to ensure 'is_bot' flag exists for compatibility (per target in per-guild map)
                    for gid, targets in list(self.monitored_bots.items()):
                        for tid, info in list(targets.items()):
                            if isinstance(info, dict) and 'is_bot' not in info:
                                info['is_bot'] = True
                    self.notification_channel_id = data.get('notification_channel_id')
                    # read per-guild channel map (if present)
                    self.notification_channel_ids = {int(k): int(v) for k, v in data.get('notification_channel_ids', {}).items()}
                    # load persisted online state mapping
                    persisted = data.get('online_status', {})
                    self.persisted_online_status = {int(gid): {int(bid): bool(val) for bid, val in bot_map.items()} for gid, bot_map in persisted.items()}
        except Exception as e:
            print(f"データ読み込みエラー: {e}")

    async def _init_online_status_cache(self):
        """サーバーごとの監視対象の初期オンライン状態をキャッシュする"""
        await self.bot.wait_until_ready()
        try:
            for guild in self.bot.guilds:
                guild_map = self.monitored_bots.get(guild.id, {})
                for bot_id in guild_map.keys():
                    bot_member = guild.get_member(bot_id)
                    is_online = False
                    if bot_member:
                        is_online = self.is_member_online(bot_member)
                    self.online_status.setdefault(guild.id, {})[bot_id] = is_online
        except Exception as e:
            print(f"オンラインステータスキャッシュ初期化中にエラー: {e}")
        # compare persisted status and notify any changes that happened while we were offline
        try:
            for guild_id, bot_map in self.online_status.items():
                for bot_id, current_online in bot_map.items():
                    prev_online = self.persisted_online_status.get(guild_id, {}).get(bot_id, None)
                    # only notify if previously known to be online but now offline, or vice versa
                    if prev_online is None:
                        # no persisted info, skip notification
                        continue
                    if prev_online and not current_online:
                        # went offline while monitor was down (or was online on disk and now offline) -> notify
                        guild = self.bot.get_guild(guild_id)
                        if not guild:
                            continue
                        guild_map = self.monitored_bots.get(guild_id, {})
                        bot_info = guild_map.get(bot_id)
                        channel_id = self.notification_channel_ids.get(guild_id)
                        channel = self.bot.get_channel(channel_id) if channel_id else None
                        if channel and bot_info:
                            await self.send_status_notification(channel, bot_info, bot_id, is_online=False, guild=guild)
                    elif not prev_online and current_online:
                        # went online while monitor was down -> notify
                        guild = self.bot.get_guild(guild_id)
                        if not guild:
                            continue
                        guild_map = self.monitored_bots.get(guild_id, {})
                        bot_info = guild_map.get(bot_id)
                        channel_id = self.notification_channel_ids.get(guild_id)
                        channel = self.bot.get_channel(channel_id) if channel_id else None
                        if channel and bot_info:
                            await self.send_status_notification(channel, bot_info, bot_id, is_online=True, guild=guild)
        except Exception as e:
            print(f"起動時の状態差分通知中にエラー: {e}")
        # set persisted to current and save
        self.persisted_online_status = {gid: {bid: val for bid, val in bots.items()} for gid, bots in self.online_status.items()}
        self.save_data()
    
    def save_data(self):
        """データを保存する"""
        try:
            data = {
                'monitored_bots': {str(gid): {str(tid): info for tid, info in targets.items()} for gid, targets in self.monitored_bots.items()},
                'notification_channel_id': self.notification_channel_id,
                'notification_channel_ids': self.notification_channel_ids
            }
            # save persisted online status
            data['online_status'] = {str(gid): {str(bid): val for bid, val in bots.items()} for gid, bots in self.persisted_online_status.items()}
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"データ保存エラー: {e}")
    
    # ========== メインコマンドグループ ==========
    
    @commands.hybrid_group(name="botmonitor", description="監視システムの管理")
    async def botmonitor(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await self.send_main_embed(ctx)
    
    @commands.has_permissions(administrator=True)
    async def send_main_embed(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🤖 監視システム",
            description="監視対象のBOTのオンライン/オフライン状態を監視します",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        channel_info = "設定されていません"
        # prefer guild specific channel
        if ctx.guild and ctx.guild.id in self.notification_channel_ids:
            channel = self.bot.get_channel(self.notification_channel_ids[ctx.guild.id])
            channel_info = channel.mention if channel else f"<#{self.notification_channel_ids[ctx.guild.id]}>"
        elif self.notification_channel_id:
            channel = self.bot.get_channel(self.notification_channel_id)
            channel_info = channel.mention if channel else f"<#{self.notification_channel_id}>"
        
        embed.add_field(name="📢 通知チャンネル", value=channel_info, inline=False)
        monitored_count = len(self.monitored_bots.get(ctx.guild.id, {}))
        embed.add_field(name="👁️ 監視中の対象数", value=f"{monitored_count}体", inline=True)
        
        # online_status is per-guild mapping, flatten counts
        # Count online in this guild only
        online_count = sum(1 for status in self.online_status.get(ctx.guild.id, {}).values() if status)
        embed.add_field(
            name="📊 現在の状態",
            value=f"✅ オンライン: {online_count}体\n📌 監視設定されている対象: {monitored_count}体",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    # ========== 通知チャンネル設定 ==========
    
    @botmonitor.command(name="channel", description="通知を送信するチャンネルを設定")
    @app_commands.describe(channel="通知を送信するチャンネル")
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        # set per-guild notification channel
        guild_id = ctx.guild.id if ctx.guild else None
        if guild_id:
            self.notification_channel_ids[guild_id] = channel.id
        else:
            # fallback to global channel id if called in DM (unlikely for admin commands)
            self.notification_channel_id = channel.id
        self.save_data()
        
        embed = discord.Embed(
            title="✅ 通知チャンネルを設定しました",
            description=f"通知を {channel.mention} に送信します（このサーバーのみ適用）",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    # ========== BOT追加（修正版）==========
    
    @botmonitor.command(name="add", description="監視対象を追加（BOT/ユーザー）")
    @app_commands.describe(
        member="監視対象のメンバー（BOTまたはユーザー）",
        notification_role="通知時にメンションするロール（任意）",
        channel="監視通知を送るチャンネルを指定（任意）"
    )
    async def add_bot(self, ctx: commands.Context, 
                     member: discord.Member, 
                     notification_role: Optional[discord.Role] = None,
                     channel: Optional[discord.TextChannel] = None):
        
        # Allow monitors of non-bot users for testing by a specific user ID
        TESTER_ID = 1290527159726637140
        # If the target is not a bot and the invoker is not the tester, reject
        if not member.bot and ctx.author.id != TESTER_ID:
            embed = discord.Embed(
                title="❌ エラー",
                description="通常のユーザーはテストユーザーのみ監視可能です。管理者はBOTのみ監視してください。",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        # if target is a bot, only admins (or the tester) can add; otherwise reject
        if member.bot is True and not ctx.author.guild_permissions.administrator and ctx.author.id != TESTER_ID:
            embed = discord.Embed(
                title="❌ エラー",
                description="BOTを追加できるのは管理者のみです。",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        # legacy: no longer strictly reject non-bot members here (handled above)
        
        guild_map = self.monitored_bots.setdefault(ctx.guild.id, {})
        if member.id in guild_map:
            embed = discord.Embed(
                title="⚠️ 既に登録されています",
                description=f"{member.mention} は既に監視対象に登録されています",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        # BOT情報を追加
        # add type info (is_bot) to the stored entry
        guild_map[member.id] = {
            'name': member.name,
            'display_name': member.display_name,
            'avatar_url': str(member.display_avatar.url),
            'role_id': notification_role.id if notification_role else None,
            'is_bot': member.bot
        }
        
        # 🔴 修正点: 初期状態を正しく判定
        is_online = self.is_member_online(member)
        # set this entity status for this guild only
        self._set_guild_bot_status(ctx.guild.id, member.id, is_online)

        # if a notification channel is specified with the add command, set it for this guild
        if channel:
            if channel.guild and channel.guild.id != ctx.guild.id:
                embed = discord.Embed(
                    title="❌ エラー",
                    description="指定したチャンネルはこのサーバーに属していません。",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed, ephemeral=True)
                return
            self.notification_channel_ids[ctx.guild.id] = channel.id
            self.save_data()
            print(f"⚙️ 通知チャンネル: guild {ctx.guild.id} -> channel {channel.id}")
        
        print(f"🔍 監視対象追加: {member.display_name} (ID: {member.id})")
        print(f"   現在のステータス: {member.status}")
        print(f"   判定結果: {'オンライン' if is_online else 'オフライン'}")
        
        self.save_data()
        
        # 応答メッセージ
        embed = discord.Embed(
            title="✅ 監視対象を追加しました",
            color=discord.Color.green()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        typ = "BOT" if member.bot else "ユーザー"
        embed.add_field(name=f"監視対象 ({typ})", value=f"{member.display_name} ({member.name})", inline=True)
        embed.add_field(name="対象 ID", value=f"`{member.id}`", inline=True)
        embed.add_field(
            name="初期状態", 
            value="✅ **オンライン**" if is_online else "❌ **オフライン**", 
            inline=True
        )
        
        if notification_role:
            embed.add_field(name="通知ロール", value=notification_role.mention, inline=True)
        if channel:
            embed.add_field(name="通知チャンネル", value=channel.mention, inline=True)
        
        embed.set_footer(text="状態変化時に通知が送信されます")
        
        await ctx.send(embed=embed)
    
    # 🔴 新規追加: メンバーのオンライン状態を判定する関数
    def is_member_online(self, member: discord.Member) -> bool:
        """メンバーがオンラインかどうかを確実に判定"""
        # discord.py 2.0以降では、statusだけでなく各プラットフォームのステータスもチェック
        if hasattr(member, 'raw_status'):
            # raw_status があればそれを使う
            return member.raw_status != 'offline'
        else:
            # 古い方法での判定
            return (
                member.status != discord.Status.offline or
                (hasattr(member, 'desktop_status') and member.desktop_status != discord.Status.offline) or
                (hasattr(member, 'web_status') and member.web_status != discord.Status.offline) or
                (hasattr(member, 'mobile_status') and member.mobile_status != discord.Status.offline)
            )

    def _get_guild_bot_status(self, guild_id: int, bot_id: int) -> bool:
        return self.online_status.get(guild_id, {}).get(bot_id, False)

    def _set_guild_bot_status(self, guild_id: int, bot_id: int, value: bool):
        prev = self._get_guild_bot_status(guild_id, bot_id)
        if prev == value:
            return
        self.online_status.setdefault(guild_id, {})[bot_id] = value
        # persist change so we can detect transitions across restarts
        self.persisted_online_status.setdefault(guild_id, {})[bot_id] = value
        self.save_data()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Presence の変化を即時に検知して通知を送る"""
        try:
            # only react to changes for monitored targets (bot or user) in this guild
            guild = after.guild
            if not guild:
                return
            guild_map = self.monitored_bots.get(guild.id, {})
            bot_id = after.id
            if bot_id not in guild_map:
                return

            before_online = self.is_member_online(before) if before else self._get_guild_bot_status(guild.id, bot_id)
            after_online = self.is_member_online(after)
            if before_online == after_online:
                return

            # 変更があれば通知チャンネルを探す (guild-specific only)
            channel_id = self.notification_channel_ids.get(guild.id)
            if not channel_id:
                print("通知チャンネルが設定されていません。on_member_update通知をスキップします。")
                return
            notification_channel = self.bot.get_channel(channel_id)
            if not notification_channel:
                print(f"通知チャンネルが見つかりません: {channel_id}")
                return

            bot_info = guild_map.get(bot_id)
            if not bot_info:
                return
            # 状態変化の通知 for this target only
            await self.send_status_notification(notification_channel, bot_info, bot_id, is_online=after_online, guild=guild)
            self._set_guild_bot_status(guild.id, bot_id, after_online)
            print(f"📣 on_member_update: {bot_info['display_name']} ({bot_id}) in {guild.name}: {before_online} -> {after_online}")
        except Exception as e:
            print(f"on_member_update中のエラー: {e}")
    
    # ========== BOT削除 ==========
    
    @botmonitor.command(name="remove", description="監視対象を削除")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(bot_id="削除するBOTのID")
    async def remove_bot(self, ctx: commands.Context, bot_id: str):
        try:
            bot_id_int = int(bot_id)
        except ValueError:
            embed = discord.Embed(
                title="❌ エラー",
                description="有効なIDを指定してください",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        
        guild_map = self.monitored_bots.get(ctx.guild.id, {})
        if bot_id_int in guild_map:
            bot_info = guild_map[bot_id_int]
            del guild_map[bot_id_int]
            # remove per-guild entries for this guild
            if ctx.guild.id in self.online_status and bot_id_int in self.online_status[ctx.guild.id]:
                del self.online_status[ctx.guild.id][bot_id_int]
            if ctx.guild.id in self.persisted_online_status and bot_id_int in self.persisted_online_status[ctx.guild.id]:
                del self.persisted_online_status[ctx.guild.id][bot_id_int]
            self.save_data()
            
            embed = discord.Embed(
                title="🗑️ 監視対象を削除しました",
                description=f"**{bot_info['display_name']}** の監視を停止しました",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ エラー",
                description="指定された対象は監視対象に登録されていません",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
    
    # ========== 一覧表示 ==========
    
    @botmonitor.command(name="list", description="監視対象の一覧を表示")
    @commands.has_permissions(administrator=True)
    async def list_bots(self, ctx: commands.Context):
        guild_map = self.monitored_bots.get(ctx.guild.id, {})
        if not guild_map:
            embed = discord.Embed(
                title="📋 監視対象一覧",
                description="監視対象はありません",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📋 監視対象一覧",
                description=f"現在 **{len(guild_map)}体** の対象を監視中",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for bot_id, bot_info in guild_map.items():
            status = "✅ オンライン" if self._get_guild_bot_status(ctx.guild.id, bot_id) else "❌ オフライン"
            role_info = f"<@&{bot_info['role_id']}>" if bot_info['role_id'] else "なし"
            
            bot_member = ctx.guild.get_member(bot_id)
            mention = bot_member.mention if bot_member else f"`{bot_id}`"
            
            typ = "BOT" if bot_info.get('is_bot', True) else "ユーザー"
            embed.add_field(
                name=f"{bot_info['display_name']}",
                value=(
                    f"状態: {status}\n"
                    f"ID: `{bot_id}`\n"
                    f"種別: {typ}\n"
                    f"通知ロール: {role_info}\n"
                    f"メンション: {mention}"
                ),
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    # ========== 状態表示 ==========
    
    @botmonitor.command(name="status", description="監視対象の現在の状態を表示")
    @commands.has_permissions(administrator=True)
    async def show_status(self, ctx: commands.Context):
        guild_map = self.monitored_bots.get(ctx.guild.id, {})
        if not guild_map:
            embed = discord.Embed(
                title="📊 現在の状態",
                description="監視対象はありません",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        online_bots = []
        offline_bots = []

        for bot_id, bot_info in guild_map.items():
            bot_member = ctx.guild.get_member(bot_id)
            mention = bot_member.mention if bot_member else bot_info['display_name']
            typ = "BOT" if bot_info.get('is_bot', True) else "ユーザー"
            if self._get_guild_bot_status(ctx.guild.id, bot_id):
                online_bots.append(f"✅ {mention} ({typ})")
            else:
                offline_bots.append(f"❌ {mention} ({typ})")

        embed = discord.Embed(
            title="📊 監視対象 現在の状態",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        if online_bots:
            embed.add_field(
                name=f"✅ オンライン ({len(online_bots)}体)",
                value="\n".join(online_bots),
                inline=False
            )

        if offline_bots:
            embed.add_field(
                name=f"❌ オフライン ({len(offline_bots)}体)",
                value="\n".join(offline_bots),
                inline=False
            )

        await ctx.send(embed=embed)

    @botmonitor.command(name="debug", description="監視タスクの状態を確認（管理者のみ）")
    @commands.has_permissions(administrator=True)
    async def debug(self, ctx: commands.Context):
        """管理者向け:監視タスクの稼働状況、最後のチェック時刻、対象数などのデバッグ情報を出力します"""
        info = []
        info.append(f"監視タスク: {'実行中' if self.monitoring_task and not self.monitoring_task.done() else '未起動/終了'}")
        info.append(f"最後のチェック: {getattr(self, 'last_check', None)}")
        info.append(f"監視対象ギルド数: {len(self.monitored_bots)}")
        for gid, targets in self.monitored_bots.items():
            count = len(targets)
            channel = self.notification_channel_ids.get(gid)
            info.append(f"  guild {gid}: {count} targets, channel: {channel}")
        embed = discord.Embed(title="🛠️ Bot Monitor Debug Info", description="\n".join(info), color=discord.Color.blue())
        await ctx.send(embed=embed)
    
    # ========== 監視機能（修正版）==========
    
    async def start_monitoring(self):
        """BOTの状態監視を開始"""
        await self.bot.wait_until_ready()
        print("🚀 監視を開始します...")
        self.last_check = None
        # 初期オンラインステータスを取得して差分通知を行う
        await self._init_online_status_cache()
        
        while not self.bot.is_closed():
            try:
                await self.check_bot_statuses()
                await asyncio.sleep(self.CHECK_INTERVAL_SECONDS)  # default 60秒ごとにチェック
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ 監視中にエラー: {e}")
                # wait a bit before retrying; keep consistent with the check interval
                await asyncio.sleep(self.CHECK_INTERVAL_SECONDS)
    
    async def check_bot_statuses(self):
        """すべての監視対象の状態をチェック"""
        # No global guard: always run the check to maintain state cache and logs; notifications will only be sent for guilds with configured channels
        
        # We'll check per-guild channels; if a guild does not have a channel configured, skip sending notifications in that guild
        
        total_targets = sum(len(m) for m in self.monitored_bots.values())
        print(f"\n🔄 状態チェック開始 ({total_targets}個の対象をチェック) - {datetime.now().isoformat()}")
        self.last_check = datetime.now()
        
        for guild in self.bot.guilds:
            target_count = len(self.monitored_bots.get(guild.id, {}))
            print(f"  🔎 ギルド: {guild.name} ({guild.id}) チェック対象数: {target_count} / 通知チャンネル設定: {'あり' if guild.id in self.notification_channel_ids else 'なし'}")
            guild_map = self.monitored_bots.get(guild.id, {})
            if not guild_map:
                continue
            for bot_id, bot_info in guild_map.items():
                bot_member = guild.get_member(bot_id)
                # select the channel for this guild (no global fallback; only notify in the configured guild)
                channel_id = self.notification_channel_ids.get(guild.id)
                if not channel_id:
                    # no notification channel for this guild, skip
                    continue
                notification_channel = self.bot.get_channel(channel_id)
                if not notification_channel:
                    print(f"❌ 通知チャンネルが見つかりません: {channel_id} (guild {guild.id})")
                    continue
                
                if not bot_member:
                    # BOTがサーバーに見つからない場合
                    print(f"  ❌ {bot_info['display_name']}: サーバーに見つかりません")
                    was_online = self._get_guild_bot_status(guild.id, bot_id)
                    if was_online:
                        print(f"  ⚠️ {bot_info['display_name']}: オフラインに変化")
                        await self.send_status_notification(
                            notification_channel,
                            bot_info,
                            bot_id,
                            is_online=False,
                            guild=guild
                        )
                        self._set_guild_bot_status(guild.id, bot_id, False)
                    continue
                
                # 🔴 修正点: 状態判定を改善
                was_online = self._get_guild_bot_status(guild.id, bot_id)
                is_online_now = self.is_member_online(bot_member)
                
                print(f"  👤 {bot_info['display_name']}: {bot_member.status} -> {'オンライン' if is_online_now else 'オフライン'}")
                
                # 状態が変化したかチェック
                if was_online and not is_online_now:
                    print(f"  🔔 {bot_info['display_name']}: オンライン → オフライン (通知送信)")
                    await self.send_status_notification(
                        notification_channel, 
                        bot_info, 
                        bot_id, 
                        is_online=False,
                        guild=guild
                    )
                elif not was_online and is_online_now:
                    print(f"  🔔 {bot_info['display_name']}: オフライン → オンライン (通知送信)")
                    await self.send_status_notification(
                        notification_channel, 
                        bot_info, 
                        bot_id, 
                        is_online=True,
                        guild=guild
                    )
                
                # 状態を更新
                self._set_guild_bot_status(guild.id, bot_id, is_online_now)
        
        print("✅ 状態チェック完了")
    
    async def send_status_notification(self, channel, bot_info, bot_id, is_online: bool, guild):
        """状態変化の通知を送信"""
        role_mention = ""
        if bot_info.get('role_id'):
            role_mention = f"<@&{bot_info['role_id']}> "
        
        if is_online:
            embed = discord.Embed(
                title="✅ BOTがオンラインになりました",
                description=f"{role_mention}監視対象のBOTがオンラインになりました",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
        else:
            embed = discord.Embed(
                title="❌ BOTがオフラインになりました",
                description=f"{role_mention}監視対象のBOTがオフラインになりました",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
        
        embed.add_field(name="対象名", value=bot_info['display_name'], inline=True)
        embed.add_field(name="対象 ID", value=f"`{bot_id}`", inline=True)
        embed.add_field(name="サーバー", value=guild.name, inline=True)
        
        if 'avatar_url' in bot_info:
            embed.set_thumbnail(url=bot_info['avatar_url'])
        
        embed.set_footer(text="監視システム")
        
        # If we are sending an 'online' notification but the persisted state already shows online, skip to avoid duplicates
        if is_online:
            prev_online = self.persisted_online_status.get(guild.id, {}).get(bot_id, None)
            if prev_online is True:
                print(f"通知スキップ: 既にオンラインと記録されています: {bot_info['display_name']} ({bot_id}) in {guild.name}")
                return
        try:
            await channel.send(embed=embed)
            # Save persisted_online_status if we've successfully notified that state change
            # We only update persisted_online_status here for clarity; _set_guild_bot_status also persists when actual state changes
            self.persisted_online_status.setdefault(guild.id, {})[bot_id] = is_online
            self.save_data()
        except Exception as e:
            print(f"通知送信に失敗しました: {e}")

async def setup(bot: commands.Bot):
    """Cogを追加する関数"""
    await bot.add_cog(BotMonitorCog(bot))