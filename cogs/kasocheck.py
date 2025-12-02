import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio

"""
過疎チェック Cog

保存形式: kaso_data.json
{
  guild_id: {
    channel_id: ["2025-11-27T12:34:56.123456", ...]
  }
}

コマンド:
/kasocheck days:7 top:10 backfill:false  -> サーバー全体の過疎チェック（backfill は管理者のみ）
!kasocheck 7 10 False                          -> プレフィックス版のエイリアス
"""

DATA_FILE = "kaso_data.json"
DEFAULT_RETENTION_DAYS = 30
DEFAULT_THRESHOLDS_PER_DAY = [4000, 2000, 1000, 714, 500, 300, 200, 100, 50]


def parse_period_to_days(period: str) -> int:
    """'3d', '2w', '7' のような指定を日数に変換"""
    if not period:
        return 3
    p = str(period).lower().strip()
    try:
        # 数値だけなら日数
        return int(p)
    except ValueError:
        pass
    if p.endswith("d"):
        return int(p[:-1])
    if p.endswith("w"):
        return int(p[:-1]) * 7
    # デフォルト
    return 3


class KasoCheck(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_file = DATA_FILE
        self.retention_days = DEFAULT_RETENTION_DAYS
        self.kaso_data: Dict[str, Dict[str, List[str]]] = {}
        self.thresholds = DEFAULT_THRESHOLDS_PER_DAY.copy()
        self.load_data()

    async def cog_load(self):
        # Cogがロードされたときに定期タスクを開始
        try:
            self.prune_task.start()
        except RuntimeError:
            # すでにイベントループがない場合、Botが起動時にstartされる
            pass

    async def cog_unload(self):
        self.prune_task.cancel()

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.kaso_data = json.load(f)
            except Exception as e:
                print(f"過疎チェック: データ読み込み失敗: {e}")
                self.kaso_data = {}

    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.kaso_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"過疎チェック: データ保存失敗: {e}")

    def add_message(self, guild_id: str, channel_id: str, timestamp: str):
        if guild_id not in self.kaso_data:
            self.kaso_data[guild_id] = {}
        if channel_id not in self.kaso_data[guild_id]:
            self.kaso_data[guild_id][channel_id] = []
        self.kaso_data[guild_id][channel_id].append(timestamp)
        # 一度に全部保存しないで、定期保存/終了時に保存

    def prune_old(self, guild_id: str | None = None):
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        cutoff_iso = cutoff.isoformat()
        if guild_id:
            g = self.kaso_data.get(guild_id, {})
            for ch_id, arr in list(g.items()):
                new = [t for t in arr if t >= cutoff_iso]
                self.kaso_data[guild_id][ch_id] = new
        else:
            for g_id, g in list(self.kaso_data.items()):
                for ch_id, arr in list(g.items()):
                    new = [t for t in arr if t >= cutoff_iso]
                    self.kaso_data[g_id][ch_id] = new

    @tasks.loop(hours=1)
    async def prune_task(self):
        try:
            self.prune_old()
            self.save_data()
        except Exception as e:
            print(f"過疎チェック: prune_taskで例外: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        gid = str(message.guild.id)
        cid = str(message.channel.id)
        ts = datetime.utcnow().isoformat()
        self.add_message(gid, cid, ts)

    def count_messages_in_period(self, guild_id: str, channel_id: str, days: int) -> int:
        arr = self.kaso_data.get(guild_id, {}).get(channel_id, [])
        if not arr:
            return 0
        cutoff = datetime.utcnow() - timedelta(days=days)
        return sum(1 for t in arr if t >= cutoff.isoformat())

    def count_messages_in_period_range(self, guild_id: str, channel_id: str, start: datetime, end: datetime) -> int:
        arr = self.kaso_data.get(guild_id, {}).get(channel_id, [])
        if not arr:
            return 0
        return sum(1 for t in arr if start.isoformat() <= t <= end.isoformat())

    # Removed the old `kaso` prefix command group and its fine-grained subcommands

    async def _backfill_channel(self, channel: discord.TextChannel, limit: Optional[int] = None, days: Optional[int] = None, save_every: int = 200):
        """チャネルの履歴をさかのぼって `kaso_data` に追加するヘルパー。
        - `limit`: 最大取得メッセージ数（Noneなら全取得）
        - `days`: 直近n日分のみ（Noneなら全取得）
        - `save_every`: 何件ごとにディスクに保存するか
        """
        after = None
        if days is not None:
            after = datetime.utcnow() - timedelta(days=days)
        count = 0
        async for m in channel.history(limit=limit, after=after, oldest_first=True):
            if m.author.bot:
                continue
            gid = str(m.guild.id) if m.guild else None
            cid = str(m.channel.id)
            ts = m.created_at.isoformat()
            if gid:
                self.add_message(gid, cid, ts)
                count += 1
            # throttle a bit to avoid hitting heavy rate limits
            if count % save_every == 0:
                try:
                    self.save_data()
                except Exception as e:
                    print(f"過疎チェック: 保存失敗: {e}")
                await asyncio.sleep(0.5)
        # 最終保存
        self.save_data()
        return count

    def build_guild_summary_embed(self, guild: discord.Guild, days: int, top: int = 10) -> discord.Embed:
        gid = str(guild.id)
        counts = []
        for ch_id, arr in self.kaso_data.get(gid, {}).items():
            cnt = self.count_messages_in_period(gid, ch_id, days)
            channel = guild.get_channel(int(ch_id))
            # format mention (if channel exists) and store safe name
            mention = channel.mention if channel else f"(ID:{ch_id})"
            name = f"{channel.name}" if channel else f"(ID:{ch_id})"
            counts.append((ch_id, name, mention, cnt))
        counts.sort(key=lambda x: x[3], reverse=True)
        total = sum(x[3] for x in counts)
        top_lines = []
        for i, (ch_id, name, mention, cnt) in enumerate(counts[:top], start=1):
            pct_val = (cnt / total * 100) if total > 0 else 0.0
            pct = f"{pct_val:.1f}%"
            level = self.compute_kaso_level(cnt, days)
            # draw bar based on percent of server total (not per-channel level)
            bar = self.draw_activity_bar(pct_val, length=8)
            top_lines.append(f"#{i} {mention} {bar} {self.format_number(cnt)} ({pct}) - レベル{level}")
        # Compute guild level based on server total (per-day average of all messages)
        channels_tracked = len(counts)
        per_channel_avg = total / channels_tracked if channels_tracked else 0
        guild_level_server = self.compute_kaso_level(int(total), days)
        guild_level_per_channel = self.compute_kaso_level(int(per_channel_avg), days)
        # color and title use server-level (total) as primary
        color = self.level_to_color(guild_level_server)
        status_text = self.status_label_by_level(guild_level_server)
        # add author and guild icon to make it distinctive
        embed = discord.Embed(title=f"{status_text} (レベル{guild_level_server})", description=f"{self.status_description(guild_level_server)}", color=color)
        try:
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
        except Exception:
            pass
        try:
            bot_user = self.bot.user
            if bot_user and bot_user.avatar:
                embed.set_author(name=bot_user.name, icon_url=bot_user.avatar.url)
        except Exception:
            pass

        # Statistics field
        activity_level = 11 - guild_level_server
        stats_lines = []
        stats_lines.append(f"過疎レベル (サーバー): {self.level_label(guild_level_server)}")
        stats_lines.append(f"過疎レベル (チャンネル平均): {self.level_label(guild_level_per_channel)}")
        stats_lines.append(f"活発度: {self.format_number(activity_level)} / 10")
        stats_lines.append(f"合計メッセージ: {self.format_number(total)} 件")
        stats_lines.append(f"調査チャンネル: {channels_tracked} チャンネル")
        stats_lines.append(f"調査期間: 過去{days}日間")
        embed.add_field(name="📊 統計情報", value="\n".join(stats_lines), inline=False)

        # top channels (truncate if too long)
        top_field = self._join_lines_with_limit(top_lines, limit=1024)
        embed.add_field(name="🏆 上位チャンネル", value=top_field if top_field else "データがありません", inline=False)

        # channel list (partial)
        lines = []
        for ch_id, name, mention, cnt in counts[:50]:
            lines.append(f"{mention} - {self.format_number(cnt)} 件")
        # channel list (partial) - respects 1024 char limit
        channels_field = self._join_lines_with_limit(lines, limit=1024)
        embed.add_field(name="📋 調査チャンネル一覧", value=channels_field if channels_field else "データがありません", inline=False)
        embed.set_footer(text=f"合計: {self.format_number(total)} メッセージ")
        return embed

    def format_number(self, n: int) -> str:
        try:
            return f"{n:,}"
        except Exception:
            return str(n)

    def draw_activity_bar(self, percent: float, length: int = 10) -> str:
        """Return a progress bar (emoji-based) representing percentage 0..100.
        Filled units are green, mid are yellow, last are red; empty are white squares.
        """
        p = max(0.0, min(percent, 100.0))
        filled = int(round(p / 100.0 * length))
        bar = []
        for i in range(length):
            if i < filled:
                # color by how full the bar is
                if p >= 75:
                    bar.append("🟩")
                elif p >= 40:
                    bar.append("🟨")
                else:
                    bar.append("🟥")
            else:
                bar.append("⬜")
        return "".join(bar)

    def level_to_color(self, level: int) -> int:
        # lower level = more active -> green; higher level = more sparse -> red
        if level <= 3:
            return 0x1DB954  # bright green
        if level <= 6:
            return 0xF1C40F  # yellow
        return 0xE74C3C  # red

    def level_label(self, level: int) -> str:
        # return color square + text
        if level <= 3:
            sq = "🟩"
        elif level <= 6:
            sq = "🟨"
        else:
            sq = "🟥"
        return f"{sq} レベル {level}"

    # The command to view thresholds is registered in `setup` to ensure it's in the bot tree.

    def status_label_by_level(self, level: int) -> str:
        if level <= 2:
            return "超活発なサーバー！"
        if level <= 4:
            return "活発なサーバー！"
        if level <= 6:
            return "やや活発なサーバー"
        if level <= 8:
            return "静かなサーバー"
        return "過疎気味のサーバー"

    def status_description(self, level: int) -> str:
        if level <= 2:
            return "非常に人が多い活発な状態です。"
        if level <= 4:
            return "活気のある状態です！"
        if level <= 6:
            return "やや落ち着いた活動です。"
        if level <= 8:
            return "最近は静かです。"
        return "過疎化が進んでいます。"

    def _join_lines_with_limit(self, lines: list[str], limit: int = 1024, joiner: str = "\n") -> str:
        """Join a list of lines into a single string that fits within `limit` characters.
        If abbreviated, append a "...and N more" suffix as long as it fits.
        """
        if not lines:
            return ""
        out = lines[0]
        for i, ln in enumerate(lines[1:], start=1):
            # will fit the joiner + line?
            if len(out) + len(joiner) + len(ln) <= limit:
                out = out + joiner + ln
                continue
            # try to append a summary
            remaining = len(lines) - i
            suffix = f"\n...and {remaining} more"
            if len(out) + len(suffix) <= limit:
                out += suffix
            # else don't append anything
            return out
        return out

    def compute_kaso_level(self, count: int, days: int = 1) -> int:
        """Convert raw message count into a 1..10 level.
        - Level 1 = very active (>=5000 messages)
        - Level 10 = very sparse (<200 messages)
        Thresholds are chosen to be nonlinear and can be adjusted.
        """
        # thresholds descending: boundary for level 1..9; below last => 10
        # New thresholds aim to make 9000 -> level 2
        # level 1: extremely active >= 20000
        # level 2: very active >= 9000
        # level 3: active >= 5000
        # level 4: decent >= 3000
        # level 5: moderate >= 2000
        # level 6: low >= 1000
        # level 7: quieter >= 800
        # level 8: quiet >= 400
        # level 9: very quiet >= 200
        # thresholds are per-day values; convert based on `days` into per-period thresholds
        per_day_thresholds = getattr(self, 'thresholds', DEFAULT_THRESHOLDS_PER_DAY)
        daily_avg = (count / days) if days > 0 else count
        for idx, th in enumerate(per_day_thresholds, start=1):
            if daily_avg >= th:
                return idx
        return 10

    @commands.command(name='kasocheck')
    async def kasocheck_prefix(self, ctx, days: int = 7, top: int = 10, backfill: bool = False):
        """Prefix command alias for kasocheck. Usage: !kasocheck [days] [top] [backfill:bool]"""
        if not ctx.guild:
            await ctx.send('このコマンドはサーバー内でのみ使用できます。')
            return
        if backfill and not ctx.author.guild_permissions.administrator:
            await ctx.send('バックフィルは管理者のみ実行できます。')
            return
        # Optional backfill
        if backfill:
            total_b = 0
            failed = 0
            msg = await ctx.send('バックフィルを開始します。進行中はメッセージを更新します。')
            for ch in ctx.guild.channels:
                if not isinstance(ch, discord.TextChannel):
                    continue
                perms = ch.permissions_for(ctx.guild.me)
                if not perms.read_message_history:
                    continue
                try:
                    cnt = await self._backfill_channel(ch, days=days)
                    total_b += cnt
                    await msg.edit(content=f'進行中: {ch.name} を取り込み {cnt} 件 (合計 {total_b})')
                except Exception as e:
                    failed += 1
            await msg.edit(content=f'バックフィル完了: 合計 {total_b} 件。失敗チャンネル: {failed}')
        embed = self.build_guild_summary_embed(ctx.guild, days, top)
        await ctx.send(embed=embed)

    # removed leftover prefix backfill functions


async def setup(bot):
    await bot.add_cog(KasoCheck(bot))

    # Removed the old /kaso slash commands group - keeping only the single `/kasocheck` command

    # removed /kaso group entirely

    @app_commands.command(name='kasocheck', description='サーバー全体の過疎チェックを実行します（必要ならバックフィルも実行可）')
    @app_commands.describe(days='直近n日', top='上位Nチャンネルを表示', backfill='trueにすると履歴をバックフィルします（管理者限定、時間がかかります）')
    async def kasocheck_slash(interaction: discord.Interaction, days: int = 7, top: int = 10, backfill: bool = False):
        await interaction.response.defer(ephemeral=False)
        cog = bot.get_cog('KasoCheck')
        if not cog:
            await interaction.followup.send('Cogが見つかりません。', ephemeral=True)
            return
        if not interaction.guild:
            await interaction.followup.send('このコマンドはサーバー内でのみ使用できます。', ephemeral=True)
            return
        # If backfill requested, ensure user is admin
        if backfill and not interaction.user.guild_permissions.administrator:
            await interaction.followup.send('バックフィルは管理者のみ実行できます。', ephemeral=True)
            return
        # Optional backfill: iterate channels, call _backfill_channel
        if backfill:
            total_b = 0
            failed = 0
            for ch in interaction.guild.channels:
                if not isinstance(ch, discord.TextChannel):
                    continue
                perms = ch.permissions_for(interaction.guild.me)
                if not perms.read_message_history:
                    continue
                try:
                    cnt = await cog._backfill_channel(ch, days=days)
                    total_b += cnt
                except Exception as e:
                    failed += 1
                    print(f"過疎チェック: {ch.name} の取り込み失敗: {e}")
                    await interaction.followup.send(f"バックフィル終了: 合計 {total_b} 件を取り込みました。失敗チャンネル: {failed}")
        # Build the embed using the shared helper which includes levels, stats and formatting
        embed = cog.build_guild_summary_embed(interaction.guild, days, top)
        await interaction.followup.send(embed=embed)

    bot.tree.add_command(kasocheck_slash)

    @app_commands.command(name='kasocheck_thresholds', description='過疎レベルのしきい値を表示します（管理者向け）')
    async def kasocheck_thresholds(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cog = bot.get_cog('KasoCheck')
        if not cog:
            await interaction.followup.send('Cogが見つかりません。', ephemeral=True)
            return
        if not interaction.guild:
            await interaction.followup.send('このコマンドはサーバー内でのみ使用できます。', ephemeral=True)
            return
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send('管理者のみ実行できます。', ephemeral=True)
            return
        thresholds = getattr(cog, 'thresholds', DEFAULT_THRESHOLDS_PER_DAY)
        lines = []
        for i, th in enumerate(thresholds, start=1):
            lines.append(f"レベル {i}: >= {cog.format_number(th)} 件/日 (週: {cog.format_number(int(th*7))} 件)")
        lines.append(f"レベル 10: < {cog.format_number(thresholds[-1])} 件/日 (週: < {cog.format_number(int(thresholds[-1]*7))} 件)")
        await interaction.followup.send('\n'.join(lines), ephemeral=True)

    bot.tree.add_command(kasocheck_thresholds)
