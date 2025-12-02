import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord.ui import View, Button
import aiohttp
import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Optional

CACHE_FILE = Path(__file__).resolve().parents[1] / 'pokedex_cache.json'
POKEAPI_BASE = 'https://pokeapi.co/api/v2'
ITEMS_PER_PAGE = 10

# small helper to convert katakana to hiragana

def katakana_to_hiragana(s: str) -> str:
    out = []
    for ch in s:
        code = ord(ch)
        # Katakana range: U+30A0 - U+30FF; mapping to Hiragana by subtracting 0x60
        if 0x30A0 <= code <= 0x30FF:
            out.append(chr(code - 0x60))
        else:
            out.append(ch)
    return ''.join(out)


class PokeListView(View):
    def __init__(self, bot, entries: List[Dict], page: int = 0):
        super().__init__(timeout=600)
        self.bot = bot
        self.entries = entries
        self.page = page

    async def update_message(self, interaction: Interaction):
        start = self.page * ITEMS_PER_PAGE
        slice_ = self.entries[start:start + ITEMS_PER_PAGE]
        embed = discord.Embed(title=f'ポケモン一覧 ({start + 1} - {start + len(slice_)}/{len(self.entries)})', color=0xFFCB05)
        for e in slice_:
            # show id, japanese, english
            jap = e.get('name_ja_hrkt') or e.get('name_ja') or e.get('name')
            en = e.get('name')
            embed.add_field(name=f"#{e.get('id')} {jap}", value=en, inline=False)
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception:
            # fallback to followup
            try:
                await interaction.followup.send(embed=embed, view=self)
            except Exception:
                pass

    @discord.ui.button(label='前へ', style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: Interaction, button: Button):
        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label='次へ', style=discord.ButtonStyle.secondary)
    async def next(self, interaction: Interaction, button: Button):
        if (self.page + 1) * ITEMS_PER_PAGE < len(self.entries):
            self.page += 1
            await self.update_message(interaction)


class PokedexCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session: aiohttp.ClientSession = None
        self._species_cache: Optional[List[Dict]] = None
        bot.loop.create_task(self._ensure_session())

    async def _ensure_session(self):
        await self.bot.wait_until_ready()
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def _load_cache(self):
        if self._species_cache is not None:
            return
        # try to load file cache
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    self._species_cache = json.load(f)
                    return
            except Exception:
                pass

        # else call API to build cache
        if not self.session:
            await self._ensure_session()
        url = f'{POKEAPI_BASE}/pokemon-species?limit=10000'
        async with self.session.get(url) as resp:
            if resp.status != 200:
                self._species_cache = []
                return
            data = await resp.json()
            results = data.get('results', [])

        # fetch details concurrently
        sem = asyncio.Semaphore(10)
        async def fetch_one(item):
            async with sem:
                async with self.session.get(item['url']) as r:
                    if r.status != 200:
                        return None
                    d = await r.json()
                    # find names
                    names = d.get('names', [])
                    name_ja = None
                    name_ja_hrkt = None
                    for n in names:
                        if n.get('language', {}).get('name') == 'ja-Hrkt':
                            name_ja_hrkt = n.get('name')
                        if n.get('language', {}).get('name') == 'ja':
                            name_ja = n.get('name')
                    return {
                        'id': d.get('id'),
                        'name': d.get('name'),
                        'name_ja': name_ja,
                        'name_ja_hrkt': name_ja_hrkt,
                        'url': item['url'],
                    }

        tasks = [asyncio.create_task(fetch_one(it)) for it in results]
        out = []
        for t in asyncio.as_completed(tasks):
            v = await t
            if v:
                out.append(v)
        # sort by id
        out.sort(key=lambda x: x['id'])
        self._species_cache = out
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._species_cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    async def _search_by_kana(self, kana: str) -> List[Dict]:
        # normalize kana to hiragana
        kana = katakana_to_hiragana(kana)
        await self._load_cache()
        out = []
        for s in self._species_cache:
            candidate = s.get('name_ja_hrkt') or s.get('name_ja') or s.get('name')
            if not candidate:
                continue
            # convert katakana candidate to hiragana for matching
            candidate_norm = katakana_to_hiragana(candidate)
            if candidate_norm.startswith(kana):
                out.append(s)
        return out

    async def _fetch_pokemon(self, name_or_id: str) -> Optional[Dict]:
        if not self.session:
            await self._ensure_session()
        url = f'{POKEAPI_BASE}/pokemon/{name_or_id.lower()}'
        async with self.session.get(url) as r:
            if r.status != 200:
                return None
            data = await r.json()
            # get species for Japanese name
            sp_url = data.get('species', {}).get('url')
            jap_name = None
            jap_hrkt = None
            if sp_url:
                async with self.session.get(sp_url) as r2:
                    if r2.status == 200:
                        sp = await r2.json()
                        for n in sp.get('names', []):
                            if n.get('language', {}).get('name') == 'ja-Hrkt':
                                jap_hrkt = n.get('name')
                            if n.get('language', {}).get('name') == 'ja':
                                jap_name = n.get('name')
            # collect useful fields
            types = [t['type']['name'] for t in data.get('types', [])]
            sprites = data.get('sprites', {}).get('other', {}).get('official-artwork', {}).get('front_default')
            stats = {s['stat']['name']: s['base_stat'] for s in data.get('stats', [])}
            return {
                'id': data.get('id'),
                'name': data.get('name'),
                'name_ja': jap_name,
                'name_ja_hrkt': jap_hrkt,
                'types': types,
                'sprite': sprites,
                'stats': stats,
            }

    @app_commands.command(name='pokedex', description='ポケモンの情報を取得（名前 or 五十音で検索）')
    @app_commands.describe(name='ポケモン名（英語/日本語）', kana='五十音で検索する先頭のカナ（例: あ, か, さ）', page='ページ番号(五十音検索時)')
    async def pokedex(self, interaction: Interaction, name: Optional[str] = None, kana: Optional[str] = None, page: int = 1):
        await interaction.response.defer()
        if name:
            # try by id or name
            info = await self._fetch_pokemon(name)
            if not info:
                await interaction.followup.send(f'ポケモン {name} が見つかりませんでした', ephemeral=True)
                return
            embed = discord.Embed(title=f"#{info['id']} {info.get('name_ja') or info.get('name')}", description=info.get('name'), color=0x2B9F2B)
            if info.get('sprite'):
                embed.set_thumbnail(url=info.get('sprite'))
            if info.get('types'):
                embed.add_field(name='タイプ', value=', '.join(info.get('types')), inline=False)
            if info.get('stats'):
                stats = '\n'.join([f"{k}: {v}" for k, v in info['stats'].items()])
                embed.add_field(name='ステータス', value=stats, inline=False)
            await interaction.followup.send(embed=embed)
            return

        if kana:
            kana = kana.strip()
            results = await self._search_by_kana(kana)
            if not results:
                await interaction.followup.send(f'{kana} で始まるポケモンは見つかりませんでした。', ephemeral=True)
                return
            # paginate
            page_idx = max(1, page) - 1
            view = PokeListView(self.bot, results, page_idx)
            await view.update_message(interaction)
            return

        await interaction.followup.send('使い方: `/pokedex name:<name>` または `/pokedex kana:<kana>` で検索できます。', ephemeral=True)


async def setup(bot):
    await bot.add_cog(PokedexCog(bot))
