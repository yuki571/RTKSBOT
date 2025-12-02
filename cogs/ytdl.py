import discord
from discord import app_commands, Interaction
from discord.ext import commands
import yt_dlp
import os
import asyncio
import glob
import shutil
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
from typing import Optional
from discord import ButtonStyle
from discord.ui import View, Button

# settings
DOWNLOAD_DIR = Path(__file__).resolve().parents[1] / 'downloads'
MAX_ATTACHMENT_SIZE = 8 * 1024 * 1024  # 8MB by default (can be larger for boosted servers)

# Ensure download directory exists
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _find_downloaded_file_by_id(video_id: str):
    # Search for files in downloads directory that contain the video id
    pattern = str(DOWNLOAD_DIR / f"*{video_id}*.*")
    files = glob.glob(pattern)
    if files:
        # pick the newest
        files = sorted(files, key=os.path.getmtime, reverse=True)
        return files[0]
    return None


def _human_readable_size(size: int):
    # return a human-readable byte size
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"


class DownloadView(View):
    def __init__(self, owner_id: int, url: str, info: dict, bot):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.url = url
        self.info = info
        self.bot = bot

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Only allow the command user to interact
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message('このボタンはコマンド実行者のみ使用できます。', ephemeral=True)
            return False
        return True

    async def _do_download(self, interaction: Interaction, fmt: str):
        # Send an immediate ephemeral acknowledgment and start a background task
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f'ダウンロードを開始します（{fmt}）。完了したら通知します。', ephemeral=True)
            else:
                await interaction.followup.send(f'ダウンロードを開始します（{fmt}）。完了したら通知します。', ephemeral=True)
        except Exception:
            logger.warning('Failed to send initial ack, falling back to channel', exc_info=True)
            try:
                if interaction.channel:
                    await interaction.channel.send(f'ダウンロードを開始します（{fmt}）。完了したら通知します。')
            except Exception:
                logger.exception('Failed to fallback to channel for initial ack')
        loop = asyncio.get_event_loop()
        video_id = None
        # Run the heavy download work in the background
        self.bot.loop.create_task(self._background_download(interaction, fmt))
        # disable buttons while processing
        for child in self.children:
            child.disabled = True
        try:
            await interaction.edit_original_response(view=self)
        except Exception:
            pass

    async def _background_download(self, interaction: Interaction, fmt: str):
        """Perform the heavy yt-dlp download and send result when done."""
        loop = asyncio.get_event_loop()
        video_id = None
        try:
            if fmt == 'mp3':
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': str(DOWNLOAD_DIR / '%(id)s.%(ext)s'),
                    'restrictfilenames': True,
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'prefer_ffmpeg': True,
                }
            else:  # mp4
                ydl_opts = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
                    'outtmpl': str(DOWNLOAD_DIR / '%(id)s.%(ext)s'),
                    'restrictfilenames': True,
                    'noplaylist': True,
                    'merge_output_format': 'mp4',
                    'quiet': True,
                    'no_warnings': True,
                    'prefer_ffmpeg': True,
                }
            ydl = yt_dlp.YoutubeDL(ydl_opts)
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(self.url, download=True))
            if 'entries' in data:
                data = data['entries'][0]
            video_id = data.get('id')
            file_path = _find_downloaded_file_by_id(video_id)
            if not file_path:
                await interaction.followup.send('ダウンロードに失敗しました: ファイルが見つかりませんでした。', ephemeral=True)
                return
            size = os.path.getsize(file_path)
            if size <= MAX_ATTACHMENT_SIZE:
                embed = discord.Embed(title=data.get('title'), url=data.get('webpage_url'), description=f'{fmt.upper()} をダウンロードしました', color=0x00A2E8)
                if data.get('thumbnail'):
                    embed.set_thumbnail(url=data.get('thumbnail'))
                if data.get('duration'):
                    mins, secs = divmod(data.get('duration'), 60)
                    embed.add_field(name='長さ', value=f'{mins}:{secs:02d}')
                embed.add_field(name='ファイルサイズ', value=_human_readable_size(size))
                try:
                    if interaction.response.is_done():
                        await interaction.followup.send(embed=embed, file=discord.File(file_path))
                    else:
                        # If initial response not done, send response with file
                        await interaction.response.send_message(embed=embed, file=discord.File(file_path))
                except Exception:
                    try:
                        await interaction.channel.send(content=f"{data.get('title')} をダウンロードしました", file=discord.File(file_path))
                    except Exception:
                        logger.exception('Failed to send file to channel fallback')
            else:
                try:
                    if interaction.response.is_done():
                        await interaction.followup.send(f'ダウンロードは成功しましたが、ファイルが大きすぎて送信できません（{_human_readable_size(size)}）。', ephemeral=True)
                    else:
                        await interaction.response.send_message(f'ダウンロードは成功しましたが、ファイルが大きすぎて送信できません（{_human_readable_size(size)}）。', ephemeral=True)
                except Exception:
                    try:
                        await interaction.channel.send(f'ダウンロードは成功しましたが、ファイルが大きすぎて送信できません（{_human_readable_size(size)}）。')
                    except Exception:
                        logger.exception('Failed to send channel fallback for large file')
        except Exception as e:
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(f'ダウンロード中にエラーが発生しました: {e}', ephemeral=True)
                else:
                    await interaction.response.send_message(f'ダウンロード中にエラーが発生しました: {e}', ephemeral=True)
            except Exception:
                try:
                    await interaction.channel.send(f'ダウンロード中にエラーが発生しました: {e}')
                except Exception:
                    logger.exception('Failed to send channel fallback for error')
        finally:
            # cleanup
            try:
                if video_id:
                    files_to_clean = glob.glob(str(DOWNLOAD_DIR / f"{video_id}.*"))
                    for f in files_to_clean:
                        os.remove(f)
            except Exception:
                pass
        # no UI re-enable for background operation

    @discord.ui.button(label='MP3でダウンロード', style=ButtonStyle.primary)
    async def download_mp3(self, interaction: Interaction, button: Button):
        await self._do_download(interaction, 'mp3')

    @discord.ui.button(label='MP4でダウンロード', style=ButtonStyle.success)
    async def download_mp4(self, interaction: Interaction, button: Button):
        await self._do_download(interaction, 'mp4')

    @discord.ui.button(label='キャンセル', style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: Button):
        # just disable the view and notify
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content='ダウンロードをキャンセルしました。', view=self)


class YTDLCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ytdl", description="YouTube動画をダウンロードして送信します（mp3/mp4）")
    @app_commands.describe(url="YouTube等の動画URL", format="mp3かmp4を指定（省略可）")
    @app_commands.choices(format=[
        app_commands.Choice(name="mp3", value="mp3"),
        app_commands.Choice(name="mp4", value="mp4"),
    ])
    async def ytdl(self, interaction: Interaction, url: str, format: Optional[app_commands.Choice[str]] = None):
        # Try to defer the interaction for longer processing, ignore if unknown
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(thinking=True)
        except Exception:
            pass
        fmt = format.value if format else None

        loop = asyncio.get_event_loop()

        # If the format is already provided, proceed with download; otherwise show the UI
        try:
            # Extract info without downloading to show metadata
            ydlinfo_opts = { 'quiet': True, 'no_warnings': True, 'restrictfilenames': True }
            ydl_info = yt_dlp.YoutubeDL(ydlinfo_opts)
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl_info.extract_info(url, download=False))
            if 'entries' in info:
                info = info['entries'][0]
        except Exception as e:
            await interaction.followup.send(f'メタデータ取得に失敗しました: {e}', ephemeral=True)
            return

        if fmt:
            # Use a dedicated view but immediately trigger the download
            view = DownloadView(interaction.user.id, url, info, self.bot)
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(content=f'{info.get("title")} をダウンロードします（{fmt}）', view=view)
                else:
                    await interaction.response.send_message(content=f'{info.get("title")} をダウンロードします（{fmt}）', view=view)
            except Exception:
                try:
                    await interaction.channel.send(content=f'{info.get("title")} をダウンロードします（{fmt}）')
                except Exception:
                    pass
            # For immediate operation, perform the download logic directly instead of reusing the interaction
            await view._do_download(interaction, fmt)
            return

        # Build the embed with metadata and show buttons
        embed = discord.Embed(title=info.get('title'), url=info.get('webpage_url'), description='ダウンロード形式を選択してください', color=0x00A2E8)
        if info.get('thumbnail'):
            embed.set_thumbnail(url=info.get('thumbnail'))
        if info.get('duration'):
            mins, secs = divmod(info.get('duration'), 60)
            embed.add_field(name='長さ', value=f'{mins}:{secs:02d}')
        # filesize_approx may be None; show note
        filesize_approx = info.get('filesize_approx') or info.get('filesize')
        if filesize_approx:
            embed.add_field(name='推定ファイルサイズ', value=_human_readable_size(filesize_approx))
        # show view with mp3/mp4 buttons
        view = DownloadView(interaction.user.id, url, info, self.bot)
        await interaction.followup.send(embed=embed, view=view)

        # Downloads are handled via the interactive buttons (DownloadView)


async def setup(bot):
    cog = YTDLCog(bot)
    await bot.add_cog(cog)
