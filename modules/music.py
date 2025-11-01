"""
RTKS Discord Bot - 音楽・音声機能モジュール
音楽再生、キュー管理、VOICEVOX連携機能
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
import tempfile
import os
import aiohttp
import aiofiles
import random
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# ログ設定
music_logger = logging.getLogger('music')

# YouTube-DL設定
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'extractaudio': True,
    'audioformat': 'mp3',
    'audioquality': '192K',
    'playlistend': 100,  # プレイリストの最大曲数制限
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # プレイリストの場合は最初の項目を取得
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicQueue:
    def __init__(self):
        self.queue = []
        self.current = None
        self.volume = 0.5
        self.loop = False
        
    def add(self, item):
        self.queue.append(item)
        
    def get_next(self):
        if self.loop and self.current:
            return self.current
        if self.queue:
            self.current = self.queue.pop(0)
            return self.current
        return None
        
    def clear(self):
        self.queue.clear()
        
    def is_empty(self):
        return len(self.queue) == 0

class VoiceSynthesizer:
    def __init__(self):
        self.voicevox_url = "http://localhost:50021"  # VOICEVOXのデフォルトURL
        # 専用のサブフォルダを作成して整理
        self.temp_dir = os.path.join(tempfile.gettempdir(), "discord_bot_voice")
        os.makedirs(self.temp_dir, exist_ok=True)
        # 起動時に古いファイルをクリーンアップ
        self.cleanup_old_files()
        
    def cleanup_old_files(self):
        """1時間以上古い一時ファイルを削除"""
        try:
            import time
            current_time = time.time()
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > 3600:  # 1時間 = 3600秒
                        os.remove(file_path)
        except Exception as e:
            music_logger.error(f"古いファイルのクリーンアップに失敗: {e}")

    async def check_voicevox_connection(self):
        """VOICEVOXサーバーとの接続確認"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.voicevox_url}/speakers", timeout=5) as response:
                    return response.status == 200
        except:
            return False

    async def get_voicevox_speakers(self):
        """VOICEVOX話者一覧を取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.voicevox_url}/speakers") as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            music_logger.error(f"VOICEVOX話者取得エラー: {e}")
        return []

    async def generate_voice_voicevox(self, text: str, speaker_id: int = 3):
        """VOICEVOXで音声生成"""
        try:
            # ステップ1: 音声クエリ生成
            async with aiohttp.ClientSession() as session:
                query_params = {"text": text, "speaker": speaker_id}
                async with session.post(f"{self.voicevox_url}/audio_query", params=query_params) as response:
                    if response.status != 200:
                        return None
                    query_data = await response.json()

                # ステップ2: 音声合成
                headers = {"Content-Type": "application/json"}
                synthesis_params = {"speaker": speaker_id}
                async with session.post(
                    f"{self.voicevox_url}/synthesis",
                    params=synthesis_params,
                    json=query_data,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        return None
                    
                    # 音声ファイルを保存
                    audio_data = await response.read()
                    temp_file = os.path.join(self.temp_dir, f"voice_{int(datetime.now().timestamp())}.wav")
                    
                    async with aiofiles.open(temp_file, 'wb') as f:
                        await f.write(audio_data)
                    
                    return temp_file
        except Exception as e:
            music_logger.error(f"VOICEVOX音声生成エラー: {e}")
        return None

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_queues: Dict[int, MusicQueue] = {}
        self.voice_synthesizer = VoiceSynthesizer()
        
    def get_music_queue(self, guild_id: int) -> MusicQueue:
        """サーバー専用の音楽キューを取得"""
        if guild_id not in self.music_queues:
            self.music_queues[guild_id] = MusicQueue()
        return self.music_queues[guild_id]

    async def play_next(self, guild_id: int):
        """次の曲を再生"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild or not guild.voice_client:
                return

            voice_client = guild.voice_client
            music_queue = self.get_music_queue(guild_id)
            
        except Exception as e:
            music_logger.error(f"次の曲再生エラー: {e}")

    @app_commands.command(name="join", description="ボイスチャンネルに参加します")
    @app_commands.describe(mode="参加モード (idle/auto_read)")
    async def join(self, interaction: discord.Interaction, mode: str = "idle"):
        """ボイスチャンネルに参加"""
        try:
            if not interaction.user.voice:
                await interaction.response.send_message("❌ ボイスチャンネルに参加してください。", ephemeral=True)
                return

            channel = interaction.user.voice.channel
            
            if interaction.guild.voice_client:
                if interaction.guild.voice_client.channel == channel:
                    await interaction.response.send_message(f"✅ 既に {channel.name} に参加しています。", ephemeral=True)
                    return
                else:
                    await interaction.guild.voice_client.move_to(channel)
            else:
                await channel.connect()

            embed = discord.Embed(
                title="🎵 ボイスチャンネル参加",
                description=f"📻 {channel.name} に参加しました",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            if mode == "auto_read":
                embed.add_field(name="モード", value="🗣️ 自動読み上げ", inline=True)
            else:
                embed.add_field(name="モード", value="🎵 音楽再生", inline=True)
                
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            music_logger.error(f"ボイスチャンネル参加エラー: {e}")
            await interaction.response.send_message("❌ ボイスチャンネルへの参加に失敗しました。", ephemeral=True)

    @app_commands.command(name="leave", description="ボイスチャンネルから退出して自動読み上げを停止します")
    async def leave(self, interaction: discord.Interaction):
        """ボイスチャンネルから退出"""
        try:
            if not interaction.guild.voice_client:
                await interaction.response.send_message("❌ ボイスチャンネルに参加していません。", ephemeral=True)
                return

            channel_name = interaction.guild.voice_client.channel.name
            await interaction.guild.voice_client.disconnect()
            
            # 音楽キューをクリア
            music_queue = self.get_music_queue(interaction.guild.id)
            music_queue.clear()

            embed = discord.Embed(
                title="👋 ボイスチャンネル退出",
                description=f"📻 {channel_name} から退出しました",
                color=0xff9900,
                timestamp=datetime.now()
            )
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            music_logger.error(f"ボイスチャンネル退出エラー: {e}")
            await interaction.response.send_message("❌ ボイスチャンネルからの退出に失敗しました。", ephemeral=True)

    @app_commands.command(name="play", description="音楽またはプレイリストを再生します")
    @app_commands.describe(query="曲名、URL、または検索キーワード")
    async def play(self, interaction: discord.Interaction, query: str):
        """音楽を再生"""
        await interaction.response.defer()
        
        try:
            # ボイスチャンネル接続確認
            if not interaction.guild.voice_client:
                if interaction.user.voice:
                    await interaction.user.voice.channel.connect()
                else:
                    await interaction.followup.send("❌ ボイスチャンネルに参加してから実行してください。")
                    return

            # 音楽を検索・追加
            player = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
            music_queue = self.get_music_queue(interaction.guild.id)
            music_queue.add(player)

            embed = discord.Embed(
                title="🎵 音楽を追加",
                description=f"**{player.title}** をキューに追加しました",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            if player.thumbnail:
                embed.set_thumbnail(url=player.thumbnail)
                
            await interaction.followup.send(embed=embed)

        except Exception as e:
            music_logger.error(f"音楽再生エラー: {e}")
            await interaction.followup.send("❌ 音楽の再生に失敗しました。")

    @app_commands.command(name="pause", description="音楽を一時停止します")
    async def pause(self, interaction: discord.Interaction):
        """音楽を一時停止"""
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message("⏸️ 音楽を一時停止しました。")
        else:
            await interaction.response.send_message("❌ 再生中の音楽がありません。", ephemeral=True)

    @app_commands.command(name="resume", description="音楽の再生を再開します")
    async def resume(self, interaction: discord.Interaction):
        """音楽の再生を再開"""
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            await interaction.response.send_message("▶️ 音楽の再生を再開しました。")
        else:
            await interaction.response.send_message("❌ 一時停止中の音楽がありません。", ephemeral=True)

    @app_commands.command(name="stop", description="音楽を停止してキューをクリアします")
    async def stop(self, interaction: discord.Interaction):
        """音楽を停止"""
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            music_queue = self.get_music_queue(interaction.guild.id)
            music_queue.clear()
            await interaction.response.send_message("⏹️ 音楽を停止してキューをクリアしました。")
        else:
            await interaction.response.send_message("❌ 再生中の音楽がありません。", ephemeral=True)

    @app_commands.command(name="skip", description="現在の曲をスキップします")
    async def skip(self, interaction: discord.Interaction):
        """現在の曲をスキップ"""
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏭️ 現在の曲をスキップしました。")
        else:
            await interaction.response.send_message("❌ 再生中の音楽がありません。", ephemeral=True)

    @app_commands.command(name="queue", description="現在のキューを表示します")
    async def queue_command(self, interaction: discord.Interaction):
        """現在のキューを表示"""
        music_queue = self.get_music_queue(interaction.guild.id)
        
        if music_queue.is_empty() and not music_queue.current:
            await interaction.response.send_message("📭 キューは空です。", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎵 音楽キュー",
            color=0x00ff00,
            timestamp=datetime.now()
        )

        if music_queue.current:
            embed.add_field(
                name="🎵 現在再生中",
                value=f"**{music_queue.current.title}**",
                inline=False
            )

        if not music_queue.is_empty():
            queue_list = []
            for i, player in enumerate(music_queue.queue[:10], 1):
                queue_list.append(f"`{i}.` **{player.title}**")
            
            embed.add_field(
                name="📋 次の曲",
                value="\n".join(queue_list),
                inline=False
            )
            
            if len(music_queue.queue) > 10:
                embed.add_field(
                    name="その他",
                    value=f"他に{len(music_queue.queue) - 10}曲",
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="volume", description="音量を調整します（0-100）")
    @app_commands.describe(volume="音量レベル（0-100）")
    async def volume(self, interaction: discord.Interaction, volume: int):
        """音量を調整"""
        if not 0 <= volume <= 100:
            await interaction.response.send_message("❌ 音量は0-100の範囲で指定してください。", ephemeral=True)
            return

        if interaction.guild.voice_client and hasattr(interaction.guild.voice_client.source, 'volume'):
            interaction.guild.voice_client.source.volume = volume / 100
            music_queue = self.get_music_queue(interaction.guild.id)
            music_queue.volume = volume / 100
            await interaction.response.send_message(f"🔊 音量を {volume}% に設定しました。")
        else:
            await interaction.response.send_message("❌ 再生中の音楽がありません。", ephemeral=True)

async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(MusicCog(bot))