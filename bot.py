import discord
from discord import app_commands, Interaction
from discord.ext import commands
import os
from dotenv import load_dotenv
from DETABASE.sqlite_db import Database

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
# Optional: comma-separated list of guild IDs for immediate dev sync
DEV_GUILD_IDS = os.getenv('DEV_GUILD_IDS')
DEV_GUILD_IDS = [int(x) for x in DEV_GUILD_IDS.split(',')] if DEV_GUILD_IDS else []
intents = discord.Intents.default()
# Enable members and presences intents so the bot can track member presence and caches
intents.members = True
intents.presences = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot.db = Database(workspace_root=os.path.dirname(__file__))
tree = bot.tree

@bot.event
async def on_ready():
    print(f'ログインしました: {bot.user}')
    try:
        # Try loading cogs with individual error reporting
        cogs = ['cogs.music', 'cogs.ytdl', 'cogs.tts', 'cogs.catmeme', 'cogs.fake_chinese', 'cogs.kasocheck', 'cogs.botmonitor', 'cogs.VC_OwnerEmojiAdd']
        # add pokedex cog
        cogs.append('cogs.pokedex')
        loaded = []
        for cog in cogs:
            try:
                await bot.load_extension(cog)
                print(f'Loaded {cog}')
                loaded.append(cog)
            except Exception as e:
                print(f'Failed to load {cog}: {e}')

        # perform global sync (may take time), but also optionally sync to DEV_GUILD_IDS for immediate testing
        synced = await tree.sync()
        print(f"Global slash command sync done: {len(synced)} commands")
        if DEV_GUILD_IDS:
            for gid in DEV_GUILD_IDS:
                try:
                    ss = await tree.sync(guild=discord.Object(id=gid))
                    print(f"Synced {len(ss)} commands to guild {gid}")
                except Exception as e:
                    print(f"Guild sync failed for {gid}: {e}")

        # log registered command names for visibility
        all_cmds = [c.name for c in tree.get_commands()]
        print(f"Registered app commands: {all_cmds}")
    except Exception as e:
        print(f"Sync error: {e}")

@tree.command(name="reload", description="Cogをリロード（管理者のみ）")
@app_commands.describe(cog="リロードするCog名（例: music）")
async def reload_cog(interaction: Interaction, cog: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("管理者のみ実行できます。", ephemeral=True)
        return
    try:
        # defer the response to avoid double-ack now that reload can trigger events
        await interaction.response.defer(ephemeral=True)
        await bot.reload_extension(f'cogs.{cog}')
        await interaction.followup.send(f"cogs.{cog} をリロードしました。", ephemeral=True)
    except Exception as e:
        # If we already deferred, use followup, otherwise fall back
        try:
            await interaction.followup.send(f"リロード失敗: {e}", ephemeral=True)
        except Exception:
            await interaction.response.send_message(f"リロード失敗: {e}", ephemeral=True)

@tree.command(name="sync", description="スラッシュコマンドを同期（管理者のみ）")
async def sync_cmd(interaction: Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("管理者のみ実行できます。", ephemeral=True)
        return
    try:
        await interaction.response.defer(ephemeral=True)
        synced = await tree.sync()
        await interaction.followup.send(f"{len(synced)}個のコマンドを同期しました。", ephemeral=True)
    except Exception as e:
        try:
            await interaction.followup.send(f"同期失敗: {e}", ephemeral=True)
        except Exception:
            await interaction.response.send_message(f"同期失敗: {e}", ephemeral=True)

if bot.get_command('cog'):
    bot.remove_command('cog')

@bot.command(name="cog")
async def list_cogs(ctx):
    if str(ctx.author.id) != "1290527159726637140":
        return
    cogs = list(bot.cogs.keys())
    if not cogs:
        await ctx.author.send("現在ロードされているCogはありません。")
    else:
        await ctx.author.send("ロード中のCog一覧:\n" + "\n".join(cogs))

# debug commands removed: list_commands

bot.run(TOKEN)