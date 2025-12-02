import discord
from discord import app_commands, Interaction
from discord.ext import commands
import requests
import os

VOICEVOX_API = os.getenv('VOICEVOX_API', 'http://localhost:50021')

class TTSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reading_channels = {}  # {guild_id: channel_id}

    @app_commands.command(name="startreading", description="このチャンネルの読み上げを開始")
    async def startreading(self, interaction: Interaction, speaker: int = 1):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("管理者のみ実行できます。", ephemeral=True)
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message('先にボイスチャンネルに参加してください。', ephemeral=True)
            return
        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
        guild_id = interaction.guild.id
        self.reading_channels[guild_id] = {
            'channel_id': interaction.channel.id,
            'vc': vc,
            'speaker': speaker
        }
        await interaction.response.send_message(f'このチャンネルの読み上げを開始しました。', ephemeral=True)

    @app_commands.command(name="stopreading", description="読み上げを停止")
    async def stopreading(self, interaction: Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("管理者のみ実行できます。", ephemeral=True)
            return
        guild_id = interaction.guild.id
        if guild_id in self.reading_channels:
            vc = self.reading_channels[guild_id].get('vc')
            if vc:
                await vc.disconnect()
            del self.reading_channels[guild_id]
            await interaction.response.send_message('読み上げを停止しました。', ephemeral=True)
        else:
            await interaction.response.send_message('読み上げは開始されていません。', ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        guild_id = message.guild.id
        if guild_id not in self.reading_channels:
            return
        reading_data = self.reading_channels[guild_id]
        if message.channel.id != reading_data['channel_id']:
            return
        text = message.clean_content
        if not text:
            return
        speaker = reading_data['speaker']
        try:
            # VOICEVOX APIで音声合成
            audio_query = requests.post(f"{VOICEVOX_API}/audio_query", params={"text": text, "speaker": speaker})
            if audio_query.status_code != 200:
                print(f"VOICEVOX audio_query失敗: {audio_query.status_code}")
                return
            synthesis = requests.post(f"{VOICEVOX_API}/synthesis", params={"speaker": speaker}, data=audio_query.content)
            if synthesis.status_code != 200:
                print(f"VOICEVOX synthesis失敗: {synthesis.status_code}")
                return
            # 一時ファイル保存
            tmp_path = f"/tmp/voicevox_{message.id}.wav"
            with open(tmp_path, "wb") as f:
                f.write(synthesis.content)
            vc = reading_data['vc']
            if vc and vc.is_connected():
                vc.stop()
                vc.play(discord.FFmpegPCMAudio(tmp_path), after=lambda e: self._cleanup_file(tmp_path))
        except Exception as e:
            print(f"読み上げエラー: {e}")

    def _cleanup_file(self, path):
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass

async def setup(bot):
    await bot.add_cog(TTSCog(bot))
