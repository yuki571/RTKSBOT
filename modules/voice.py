"""
RTKS Discord Bot - VOICEVOX音声機能モジュール
音声読み上げ、話者管理、音声設定機能
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from typing import Optional, Dict, List

# ログ設定
voice_logger = logging.getLogger('voice')

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="voicelist", description="利用可能な音声話者一覧を表示します")
    async def voicelist(self, interaction: discord.Interaction):
        """利用可能な音声話者一覧を表示"""
        try:
            # VOICEVOX接続確認
            from modules.music import VoiceSynthesizer
            synthesizer = VoiceSynthesizer()
            
            if not await synthesizer.check_voicevox_connection():
                await interaction.response.send_message("❌ VOICEVOX サーバーに接続できません。", ephemeral=True)
                return

            speakers = await synthesizer.get_voicevox_speakers()
            if not speakers:
                await interaction.response.send_message("❌ 話者一覧を取得できませんでした。", ephemeral=True)
                return

            embed = discord.Embed(
                title="🗣️ VOICEVOX 話者一覧",
                color=0x00ff00,
                timestamp=datetime.now()
            )

            speaker_list = []
            for speaker in speakers[:20]:  # 最大20人まで表示
                styles = ", ".join([style["name"] for style in speaker.get("styles", [])])
                speaker_list.append(f"**{speaker['name']}** ({styles})")

            embed.add_field(
                name="利用可能な話者",
                value="\n".join(speaker_list) if speaker_list else "話者が見つかりません",
                inline=False
            )

            if len(speakers) > 20:
                embed.add_field(
                    name="その他",
                    value=f"他に{len(speakers) - 20}人の話者が利用可能です",
                    inline=False
                )

            embed.add_field(
                name="使用方法",
                value="`/setvoice` コマンドで音声を設定できます",
                inline=False
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            voice_logger.error(f"話者一覧表示エラー: {e}")
            await interaction.response.send_message("❌ 話者一覧の取得に失敗しました。", ephemeral=True)

    @app_commands.command(name="voicevox_status", description="VOICEVOX接続状態を確認します")
    async def voicevox_status(self, interaction: discord.Interaction):
        """VOICEVOX接続状態を確認"""
        try:
            from modules.music import VoiceSynthesizer
            synthesizer = VoiceSynthesizer()
            
            is_connected = await synthesizer.check_voicevox_connection()
            
            embed = discord.Embed(
                title="🔊 VOICEVOX 接続状態",
                color=0x00ff00 if is_connected else 0xff0000,
                timestamp=datetime.now()
            )
            
            if is_connected:
                embed.add_field(name="状態", value="✅ 接続済み", inline=True)
                embed.add_field(name="URL", value=synthesizer.voicevox_url, inline=True)
                
                # 話者数を取得
                speakers = await synthesizer.get_voicevox_speakers()
                embed.add_field(name="利用可能話者数", value=f"{len(speakers)}人" if speakers else "0人", inline=True)
            else:
                embed.add_field(name="状態", value="❌ 接続失敗", inline=True)
                embed.add_field(name="URL", value=synthesizer.voicevox_url, inline=True)
                embed.add_field(
                    name="対処法",
                    value="VOICEVOX エンジンが起動しているか確認してください",
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            voice_logger.error(f"VOICEVOX状態確認エラー: {e}")
            await interaction.response.send_message("❌ VOICEVOX状態の確認に失敗しました。", ephemeral=True)

    @app_commands.command(name="auto_read", description="このチャンネルの自動読み上げを設定します")
    @app_commands.describe(enabled="自動読み上げを有効にするかどうか")
    @app_commands.choices(enabled=[
        app_commands.Choice(name="有効", value="true"),
        app_commands.Choice(name="無効", value="false")
    ])
    async def auto_read(self, interaction: discord.Interaction, enabled: str):
        """自動読み上げ設定"""
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            is_enabled = enabled == "true"
            
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO guild_settings 
                    (guild_id, auto_read_channel_id, auto_read_enabled) 
                    VALUES (?, ?, ?)
                ''', (interaction.guild.id, interaction.channel.id if is_enabled else None, is_enabled))
                await db.commit()

            embed = discord.Embed(
                title="🗣️ 自動読み上げ設定",
                color=0x00ff00 if is_enabled else 0xff9900,
                timestamp=datetime.now()
            )
            
            if is_enabled:
                embed.add_field(name="状態", value="✅ 有効", inline=True)
                embed.add_field(name="対象チャンネル", value=interaction.channel.mention, inline=True)
                embed.add_field(
                    name="使い方",
                    value="ボイスチャンネルに参加してからメッセージを送信すると読み上げされます",
                    inline=False
                )
            else:
                embed.add_field(name="状態", value="❌ 無効", inline=True)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            voice_logger.error(f"自動読み上げ設定エラー: {e}")
            await interaction.response.send_message("❌ 自動読み上げの設定に失敗しました。", ephemeral=True)

    @app_commands.command(name="setvoice", description="自分の読み上げ音声を設定します")
    @app_commands.describe(
        speaker_id="話者ID（/voicelist で確認）",
        speed="読み上げ速度（0.5-2.0）",
        pitch="音の高さ（-0.15-0.15）",
        volume="音量（0.0-2.0）"
    )
    async def setvoice(self, interaction: discord.Interaction, speaker_id: int, speed: float = 1.0, pitch: float = 0.0, volume: float = 1.0):
        """読み上げ音声設定"""
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            # パラメータ検証
            if not (0.5 <= speed <= 2.0):
                await interaction.response.send_message("❌ 速度は0.5-2.0の範囲で指定してください。", ephemeral=True)
                return
            if not (-0.15 <= pitch <= 0.15):
                await interaction.response.send_message("❌ 音の高さは-0.15-0.15の範囲で指定してください。", ephemeral=True)
                return
            if not (0.0 <= volume <= 2.0):
                await interaction.response.send_message("❌ 音量は0.0-2.0の範囲で指定してください。", ephemeral=True)
                return

            # VOICEVOX接続確認
            from modules.music import VoiceSynthesizer
            synthesizer = VoiceSynthesizer()
            
            if not await synthesizer.check_voicevox_connection():
                await interaction.response.send_message("❌ VOICEVOX サーバーに接続できません。", ephemeral=True)
                return

            # データベースに保存
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO user_voice_settings 
                    (guild_id, user_id, speaker_id, speed, pitch, volume)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (interaction.guild.id, interaction.user.id, speaker_id, speed, pitch, volume))
                await db.commit()

            embed = discord.Embed(
                title="🗣️ 音声設定完了",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            embed.add_field(name="話者ID", value=speaker_id, inline=True)
            embed.add_field(name="速度", value=f"{speed:.1f}", inline=True)
            embed.add_field(name="音の高さ", value=f"{pitch:.2f}", inline=True)
            embed.add_field(name="音量", value=f"{volume:.1f}", inline=True)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            voice_logger.error(f"音声設定エラー: {e}")
            await interaction.response.send_message("❌ 音声設定に失敗しました。", ephemeral=True)

    @app_commands.command(name="myvoice", description="自分の現在の音声設定を確認します")
    async def myvoice(self, interaction: discord.Interaction):
        """現在の音声設定を確認"""
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                await interaction.response.send_message("❌ データベースが利用できません。", ephemeral=True)
                return

            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT speaker_id, speed, pitch, volume 
                    FROM user_voice_settings 
                    WHERE guild_id = ? AND user_id = ?
                ''', (interaction.guild.id, interaction.user.id))
                result = await cursor.fetchone()

            embed = discord.Embed(
                title="🗣️ 現在の音声設定",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)

            if result:
                speaker_id, speed, pitch, volume = result
                embed.add_field(name="話者ID", value=speaker_id, inline=True)
                embed.add_field(name="速度", value=f"{speed:.1f}", inline=True)
                embed.add_field(name="音の高さ", value=f"{pitch:.2f}", inline=True)
                embed.add_field(name="音量", value=f"{volume:.1f}", inline=True)
            else:
                embed.add_field(
                    name="設定状況",
                    value="音声設定がされていません。\n`/setvoice` で設定してください。",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            voice_logger.error(f"音声設定確認エラー: {e}")
            await interaction.response.send_message("❌ 音声設定の確認に失敗しました。", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        """自動読み上げ処理"""
        if message.author.bot:
            return

        try:
            await self._handle_auto_read(message)
        except Exception as e:
            voice_logger.error(f"自動読み上げ処理エラー: {e}")

    async def _handle_auto_read(self, message):
        """自動読み上げ処理"""
        try:
            from database import db_manager
            if not db_manager.is_initialized():
                return

            # 自動読み上げ設定をチェック
            import aiosqlite
            async with aiosqlite.connect(db_manager.db_path) as db:
                cursor = await db.execute('''
                    SELECT auto_read_channel_id, auto_read_enabled 
                    FROM guild_settings 
                    WHERE guild_id = ? AND auto_read_enabled = 1
                ''', (message.guild.id,))
                result = await cursor.fetchone()

                if not result or result[0] != message.channel.id:
                    return

                # ボイスクライアント確認
                voice_client = message.guild.voice_client
                if not voice_client or not voice_client.is_connected():
                    return

                # ユーザーの音声設定を取得
                cursor = await db.execute('''
                    SELECT speaker_id, speed, pitch, volume 
                    FROM user_voice_settings 
                    WHERE guild_id = ? AND user_id = ?
                ''', (message.guild.id, message.author.id))
                voice_settings = await cursor.fetchone()

                # デフォルト設定
                speaker_id = voice_settings[0] if voice_settings else 3
                speed = voice_settings[1] if voice_settings else 1.0
                pitch = voice_settings[2] if voice_settings else 0.0
                volume = voice_settings[3] if voice_settings else 1.0

                # 音声ファイル生成
                from modules.music import VoiceSynthesizer
                synthesizer = VoiceSynthesizer()
                
                # メッセージをクリーンアップ
                clean_text = self._clean_message_for_speech(message.content)
                if not clean_text:
                    return

                audio_file = await synthesizer.generate_voice_voicevox(clean_text, speaker_id)
                if audio_file:
                    # 音声再生
                    voice_client.play(discord.FFmpegPCMAudio(audio_file))

        except Exception as e:
            voice_logger.error(f"自動読み上げ処理詳細エラー: {e}")

    def _clean_message_for_speech(self, text: str) -> str:
        """メッセージを読み上げ用にクリーンアップ"""
        import re
        
        # URL を除去
        text = re.sub(r'https?://[^\s]+', 'URL', text)
        
        # メンションを名前に変換
        text = re.sub(r'<@!?(\d+)>', 'メンション', text)
        
        # チャンネルメンションを除去
        text = re.sub(r'<#(\d+)>', 'チャンネル', text)
        
        # 絵文字を除去
        text = re.sub(r'<:\w+:\d+>', '', text)
        
        # 改行を句点に変換
        text = text.replace('\n', '。')
        
        # 長すぎる場合は切り詰め
        if len(text) > 100:
            text = text[:100] + '以下略'
        
        return text.strip()

async def setup(bot):
    """Cogをボットに追加"""
    await bot.add_cog(VoiceCog(bot))