import discord
import logging
from discord import app_commands, Interaction, ButtonStyle
from discord.ext import commands
from discord.ui import Button, View
import yt_dlp
import asyncio

ffmpeg_options = {
    'options': '-vn'
}
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.thumbnail = data.get('thumbnail')
        self.webpage_url = data.get('webpage_url')
        self.duration = data.get('duration')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, volume=0.5):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data, volume=volume)

class MusicView(View):
    def __init__(self, player, voice_client, url=None, bot=None, loop_mode=False):
        super().__init__(timeout=None)
        self.player = player
        self.voice_client = voice_client
        self.url = url
        self.bot = bot
        self.loop_mode = loop_mode

    @discord.ui.button(label="⏸️ 一時停止", style=ButtonStyle.secondary)
    async def pause(self, interaction: Interaction, button: Button):
        if self.voice_client.is_playing():
            self.voice_client.pause()
            await interaction.response.send_message('一時停止しました。', ephemeral=True)
        else:
            await interaction.response.send_message('再生中の音楽がありません。', ephemeral=True)

    @discord.ui.button(label="▶️ 再開", style=ButtonStyle.success)
    async def resume(self, interaction: Interaction, button: Button):
        if self.voice_client.is_paused():
            self.voice_client.resume()
            await interaction.response.send_message('再生を再開しました。', ephemeral=True)
        else:
            await interaction.response.send_message('一時停止中の音楽がありません。', ephemeral=True)


    @discord.ui.button(label="🔁 ループ切替", style=ButtonStyle.secondary, row=1)
    async def toggle_loop(self, interaction: Interaction, button: Button):
        self.loop_mode = not self.loop_mode
        button.label = "🔁 ループ中" if self.loop_mode else "🔁 ループ切替"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f'ループ: {"ON" if self.loop_mode else "OFF"}', ephemeral=True)

    @discord.ui.button(label="⏹️ 停止", style=ButtonStyle.danger)
    async def stop(self, interaction: Interaction, button: Button):
        self.voice_client.stop()
        self.loop_mode = False
        await interaction.response.send_message('再生を停止しました。', ephemeral=True)


    @discord.ui.button(label="🔉 音量-", style=ButtonStyle.primary)
    async def vol_down(self, interaction: Interaction, button: Button):
        # 5%刻みで下げる、最小0.1%
        new_volume = max(self.player.volume - 0.05, 0.001)
        self.player.volume = new_volume
        # update guild-level stored volume if we can fetch the cog instance
        try:
            cog = self.bot.get_cog('MusicCog')
            if cog and self.voice_client.guild:
                cog.guild_volumes[self.voice_client.guild.id] = new_volume
                # persist to db
                try:
                    if hasattr(self.bot, 'db'):
                        settings = self.bot.db.load_guild_settings(str(self.voice_client.guild.id)) or {}
                        settings.setdefault('music', {})
                        settings['music']['volume'] = new_volume
                        self.bot.db.save_guild_settings(str(self.voice_client.guild.id), settings)
                except Exception:
                    pass
        except Exception:
            pass
        await interaction.response.send_message(f'音量: {new_volume*100:.1f}%', ephemeral=True)

    @discord.ui.button(label="🔊 音量+", style=ButtonStyle.primary)
    async def vol_up(self, interaction: Interaction, button: Button):
        # 5%刻みで上げる、最大200%
        new_volume = min(self.player.volume + 0.05, 2.0)
        self.player.volume = new_volume
        try:
            cog = self.bot.get_cog('MusicCog')
            if cog and self.voice_client.guild:
                cog.guild_volumes[self.voice_client.guild.id] = new_volume
                # persist to db
                try:
                    if hasattr(self.bot, 'db'):
                        settings = self.bot.db.load_guild_settings(str(self.voice_client.guild.id)) or {}
                        settings.setdefault('music', {})
                        settings['music']['volume'] = new_volume
                        self.bot.db.save_guild_settings(str(self.voice_client.guild.id), settings)
                except Exception:
                    pass
        except Exception:
            pass
        await interaction.response.send_message(f'音量: {new_volume*100:.1f}%', ephemeral=True)

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # store per-guild volume (float between 0.001 and 2.0)
        self.guild_volumes = {}
        # load persisted volumes from DB
        bot.loop.create_task(self._load_persisted_volumes())
        self.logger = logging.getLogger(__name__)

    async def _load_persisted_volumes(self):
        await self.bot.wait_until_ready()
        if not hasattr(self.bot, 'db'):
            return
        for guild in self.bot.guilds:
            try:
                settings = self.bot.db.load_guild_settings(str(guild.id)) or {}
                music_settings = settings.get('music', {})
                vol = music_settings.get('volume')
                if isinstance(vol, (int, float)):
                    self.guild_volumes[guild.id] = float(vol)
            except Exception:
                pass

    @app_commands.command(name="join", description="ボイスチャンネルに参加")
    async def join(self, interaction: Interaction):
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            try:
                self.logger.info('Attempting to connect to voice channel %s in guild %s', channel.id, interaction.guild.id)
                await channel.connect()
            except Exception as e:
                self.logger.exception('Failed to connect to voice channel')
                await interaction.response.send_message('ボイスチャンネルに接続できませんでした。', ephemeral=True)
                return
            await interaction.response.send_message('ボイスチャンネルに参加しました。', ephemeral=True)
        else:
            await interaction.response.send_message('先にボイスチャンネルに参加してください。', ephemeral=True)

    @app_commands.command(name="leave", description="ボイスチャンネルから退出")
    async def leave(self, interaction: Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message('ボイスチャンネルから退出しました。', ephemeral=True)
        else:
            await interaction.response.send_message('ボイスチャンネルに接続していません。', ephemeral=True)

    @app_commands.command(name="play", description="音楽を再生（YouTube等のURL）")
    @app_commands.describe(url="YouTube等のURL", volume="音量(0~200, デフォルト10)")
    async def play(self, interaction: Interaction, url: str, volume: int = 10):
        if not interaction.guild.voice_client:
            if interaction.user.voice:
                await interaction.user.voice.channel.connect()
            else:
                await interaction.response.send_message('先にボイスチャンネルに参加してください。', ephemeral=True)
                return
        await interaction.response.defer()
        # 音量スケール補正: 50%指定時も実質10%程度の音量になるよう調整
        # 例: 0~100% → 0~0.2 (ffmpeg/discord.pyのデフォルト基準)
        # 0~200 → 0.0~2.0, 0.1%単位まで
        vol = max(0, min(volume, 200)) / 100
        # If we have a stored per-guild volume, prefer it over the supplied value
        stored = self.guild_volumes.get(interaction.guild.id)
        if stored is not None:
            vol = stored
        player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True, volume=vol)
        # persist volume for this guild
        self.guild_volumes[interaction.guild.id] = vol
        try:
            if hasattr(self.bot, 'db'):
                settings = self.bot.db.load_guild_settings(str(interaction.guild.id)) or {}
                settings.setdefault('music', {})
                settings['music']['volume'] = vol
                self.bot.db.save_guild_settings(str(interaction.guild.id), settings)
        except Exception:
            pass
        vc = interaction.guild.voice_client
        def after_play(e):
            if hasattr(vc, 'music_view') and vc.music_view.loop_mode and not e:
                fut = asyncio.run_coroutine_threadsafe(self.play(interaction, url, int(vol*100)), self.bot.loop)
                try:
                    fut.result()
                except Exception as exc:
                    print(f'Loop error: {exc}')
        vc.stop()
        vc.play(player, after=after_play)
        embed = discord.Embed(title=player.title, url=player.webpage_url, description="再生中", color=0x1DB954)
        if player.thumbnail:
            embed.set_thumbnail(url=player.thumbnail)
        if player.duration:
            mins, secs = divmod(player.duration, 60)
            embed.add_field(name="長さ", value=f"{mins}:{secs:02d}")
        embed.add_field(name="音量", value=f"{vol*100:.1f}%")
        view = MusicView(player, vc, url=url, bot=self.bot)
        vc.music_view = view
        await interaction.followup.send(embed=embed, view=view)


    @app_commands.command(name="volume", description="音量を確認/設定します (0〜200)")
    @app_commands.describe(volume="0~200, 現在の音量を表示するには省略")
    async def volume(self, interaction: Interaction, volume: int | None = None):
        if not interaction.guild:
            await interaction.response.send_message('サーバー内でのみ使用できます。', ephemeral=True)
            return
        # defer quickly so interaction stays alive
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
        except Exception:
            pass
        if volume is None:
            vc = interaction.guild.voice_client
            current = None
            if vc and hasattr(vc, 'source') and vc.source:
                try:
                    current = getattr(vc.source, 'volume', None)
                except Exception:
                    current = None
            if current is None:
                current = self.guild_volumes.get(interaction.guild.id, 0.1)
            await interaction.followup.send(f'現在の音量: {current*100:.1f}%', ephemeral=True)
            return

        volume_val = max(0.001, min(volume/100, 2.0))
        self.guild_volumes[interaction.guild.id] = volume_val
        try:
            if hasattr(self.bot, 'db'):
                settings = self.bot.db.load_guild_settings(str(interaction.guild.id)) or {}
                settings.setdefault('music', {})
                settings['music']['volume'] = volume_val
                self.bot.db.save_guild_settings(str(interaction.guild.id), settings)
        except Exception:
            pass
        vc = interaction.guild.voice_client
        if vc and hasattr(vc, 'source') and vc.source:
            try:
                vc.source.volume = volume_val
            except Exception:
                pass
        await interaction.followup.send(f'音量を {volume_val*100:.1f}% に設定しました', ephemeral=True)


    @commands.command(name="volume")
    async def volume_text(self, ctx, vol: float | None = None):
        """!volume [数値] で音量を変更または現在の音量を表示します
        - 引数なし: 現在の音量を表示します
        - 引数あり: 0~200 の値で音量を設定します（例: !volume 5 → 5% → 0.05）"""
        if not ctx.guild:
            await ctx.send("サーバー内でのみ使用できます。")
            return
        # 引数が指定されていない場合は現在の音量を表示して終了
        if vol is None:
            vc = ctx.guild.voice_client
            current = None
            if vc and hasattr(vc, 'source') and vc.source:
                try:
                    current = getattr(vc.source, 'volume', None)
                except Exception:
                    current = None
            if current is None:
                current = self.guild_volumes.get(ctx.guild.id, 0.1)
            await ctx.send(f'現在の音量: {current*100:.1f}%')
            return

        # 0.1%単位まで下げられる
        volume = max(0.001, min(vol/100, 2.0))
        # persist the value
        try:
            self.guild_volumes[ctx.guild.id] = volume
        except Exception:
            self.guild_volumes = {ctx.guild.id: volume}
        vc = ctx.guild.voice_client
        if vc and hasattr(vc, 'source') and vc.source:
            try:
                vc.source.volume = volume
            except Exception:
                # Some sources may not support volume property; ignore
                pass
        await ctx.send(f'音量を {volume*100:.1f}% に設定しました')
        # persist to DB
        try:
            if hasattr(self.bot, 'db'):
                settings = self.bot.db.load_guild_settings(str(ctx.guild.id)) or {}
                settings.setdefault('music', {})
                settings['music']['volume'] = volume
                self.bot.db.save_guild_settings(str(ctx.guild.id), settings)
        except Exception:
            pass

async def setup(bot):
    cog = MusicCog(bot)
    await bot.add_cog(cog)
