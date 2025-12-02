import discord
from discord.ext import commands
import json
import os
from typing import Dict, Optional


class VCOwnerEmojiAdd(commands.Cog):
    """VCにおけるオーナー（最初に入った人）に 🏠 を付けるCog
    - 最初にVCに入った人をそのチャンネルのオーナーとみなし、ニックネームの後ろに🏠を追加します
    - オーナーがVCを抜けると元のニックネームに戻します（永続化して再起動にも対応）
    """

    DATA_FILE = "vc_owner_emoji.json"
    EMOJI = " 🏠"
    MAX_NICKLEN = 32

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # guild_id -> channel_id -> owner_user_id
        self.vc_owners: Dict[int, Dict[int, int]] = {}
        # guild_id -> user_id -> original_nick_or_none
        self.original_nicks: Dict[int, Dict[int, Optional[str]]] = {}
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.DATA_FILE):
            return
        try:
            with open(self.DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.vc_owners = {int(gid): {int(cid): int(uid) for cid, uid in chmap.items()} for gid, chmap in data.get("vc_owners", {}).items()}  # type: ignore
                self.original_nicks = {int(gid): {int(uid): nick for uid, nick in umap.items()} for gid, umap in data.get("original_nicks", {}).items()}  # type: ignore
        except Exception as e:
            print(f"VC_OwnerEmojiAdd: Load data error: {e}")

    def save_data(self):
        try:
            data = {
                "vc_owners": {str(gid): {str(cid): uid for cid, uid in chmap.items()} for gid, chmap in self.vc_owners.items()},
                "original_nicks": {str(gid): {str(uid): nick for uid, nick in umap.items()} for gid, umap in self.original_nicks.items()},
            }
            with open(self.DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"VC_OwnerEmojiAdd: Save data error: {e}")

    async def _set_owner(self, guild_id: int, channel_id: int, member: discord.Member):
        # store owner and original nick
        self.vc_owners.setdefault(guild_id, {})[channel_id] = member.id
        self.original_nicks.setdefault(guild_id, {})[member.id] = member.nick
        try:
            # If member already has the emoji appended, skip
            display = member.nick if member.nick is not None else member.name
            if display.endswith(self.EMOJI):
                return
            new_nick = f"{display}{self.EMOJI}"
            if len(new_nick) > self.MAX_NICKLEN:
                # truncate trim to fit
                base = display[: self.MAX_NICKLEN - len(self.EMOJI)]
                new_nick = f"{base}{self.EMOJI}"
            await member.edit(nick=new_nick)
        except Exception as e:
            print(f"VC_OwnerEmojiAdd: Failed to set owner nickname: {e}")
        finally:
            self.save_data()

    async def _clear_owner(self, guild_id: int, channel_id: int, member: discord.Member):
        # revert nickname and clear mapping
        try:
            orig = self.original_nicks.get(guild_id, {}).get(member.id)
            # If orig is None, we should remove nickname (set to None) to restore to username
            await member.edit(nick=orig)
        except Exception as e:
            print(f"VC_OwnerEmojiAdd: Failed to revert nickname: {e}")
        finally:
            # cleanup
            if guild_id in self.vc_owners and channel_id in self.vc_owners[guild_id]:
                try:
                    del self.vc_owners[guild_id][channel_id]
                except KeyError:
                    pass
            if guild_id in self.original_nicks and member.id in self.original_nicks[guild_id]:
                try:
                    del self.original_nicks[guild_id][member.id]
                except KeyError:
                    pass
            self.save_data()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # If user joined a channel
        try:
            guild = member.guild
            # handle join
            if before.channel is None and after.channel is not None:
                ch = after.channel
                # If this channel was empty (first member), set as owner
                if len(ch.members) == 1:
                    await self._set_owner(guild.id, ch.id, member)
            # handle leave
            elif before.channel is not None and after.channel is None:
                ch = before.channel
                guild_map = self.vc_owners.get(guild.id, {})
                owner_id = guild_map.get(ch.id)
                if owner_id == member.id:
                    await self._clear_owner(guild.id, ch.id, member)
            # handle user moving channels
            elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
                # leaving previous channel
                prev_ch = before.channel
                guild_map = self.vc_owners.get(member.guild.id, {})
                owner_id = guild_map.get(prev_ch.id)
                if owner_id == member.id:
                    await self._clear_owner(member.guild.id, prev_ch.id, member)
                # joining new channel: check if empty now
                new_ch = after.channel
                if len(new_ch.members) == 1:
                    await self._set_owner(member.guild.id, new_ch.id, member)
        except Exception as ex:
            print(f"VC_OwnerEmojiAdd: on_voice_state_update error: {ex}")

    async def cog_unload(self):
        # revert all nicknames we changed
        try:
            for guild_id, chmap in list(self.vc_owners.items()):
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue
                for ch_id, owner_id in list(chmap.items()):
                    try:
                        member = guild.get_member(owner_id)
                        if member:
                            # revert
                            orig = self.original_nicks.get(guild_id, {}).get(owner_id)
                            await member.edit(nick=orig)
                    except Exception:
                        pass
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(VCOwnerEmojiAdd(bot))
