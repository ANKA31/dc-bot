import asyncio
import os
from dataclasses import dataclass, field
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except ImportError:
    spotipy = None


YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch1",
    "source_address": "0.0.0.0",
}
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@dataclass
class Track:
    title: str
    source: str
    requested_by: int


@dataclass
class MusicState:
    queue: list[Track] = field(default_factory=list)
    current: Track | None = None
    panel_channel_id: int | None = None
    panel_message_id: int | None = None
    paused: bool = False
    playing: bool = False


class MusicInputModal(discord.ui.Modal, title="Müzik Başlat"):
    def __init__(self, cog, add_only=False):
        super().__init__()
        self.cog = cog
        self.add_only = add_only
        self.query = discord.ui.TextInput(
            label="Playlist, şarkı linki veya şarkı adı",
            placeholder="Spotify / YouTube Music linki veya örn. Tarkan - Dudu",
            required=True,
            max_length=500,
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        result = await self.cog.handle_request(interaction, self.query.value.strip(), self.add_only)
        await interaction.followup.send(result, ephemeral=True)


class MusicPanelView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        voice = interaction.guild.voice_client
        if interaction.user.guild_permissions.manage_guild:
            return True
        if not voice or not interaction.user.voice or interaction.user.voice.channel != voice.channel:
            await interaction.response.send_message("Bu paneli kullanmak için botla aynı ses kanalında olmalısın.", ephemeral=True)
            return False
        return True

    async def _state(self, interaction):
        return self.cog.states.get(interaction.guild.id)

    @discord.ui.button(label="Duraklat", style=discord.ButtonStyle.primary, emoji="⏯️", custom_id="music_pause")
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = await self._state(interaction)
        vc = interaction.guild.voice_client
        if not state or not vc or not vc.is_playing() and not vc.is_paused():
            await interaction.response.send_message("Şu anda çalan bir parça yok.", ephemeral=True)
            return
        if vc.is_paused():
            vc.resume()
            state.paused = False
            button.label = "Duraklat"
        else:
            vc.pause()
            state.paused = True
            button.label = "Devam Et"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Sonraki", style=discord.ButtonStyle.secondary, emoji="⏭️", custom_id="music_next")
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = await self._state(interaction)
        vc = interaction.guild.voice_client
        if not state or not vc:
            await interaction.response.send_message("Aktif müzik oturumu yok.", ephemeral=True)
            return
        if vc.is_playing() or vc.is_paused():
            vc.stop()
        await interaction.response.send_message("Sıradaki parçaya geçiliyor.", ephemeral=True)

    @discord.ui.button(label="Şarkı Ekle", style=discord.ButtonStyle.success, emoji="➕", custom_id="music_add")
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MusicInputModal(self.cog, add_only=True))

    @discord.ui.button(label="Sıra", style=discord.ButtonStyle.secondary, emoji="📃", custom_id="music_queue")
    async def queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = await self._state(interaction)
        if not state or not state.queue:
            await interaction.response.send_message("Sırada başka parça yok.", ephemeral=True)
            return
        text = "\n".join(f"{i}. {track.title}" for i, track in enumerate(state.queue[:15], 1))
        await interaction.response.send_message(f"**Müzik Sırası**\n{text}", ephemeral=True)

    @discord.ui.button(label="Durdur ve Çık", style=discord.ButtonStyle.danger, emoji="⏹️", custom_id="music_stop")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = await self._state(interaction)
        if state:
            state.queue.clear()
            state.current = None
            state.playing = False
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Müzik durduruldu ve bot ses kanalından ayrıldı.", view=self)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.states: dict[int, MusicState] = {}
        self.bot.add_view(MusicPanelView(self))
        self.spotify = self._create_spotify_client()

    def _create_spotify_client(self):
        if not spotipy:
            return None
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            return None
        try:
            return spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id, client_secret))
        except Exception:
            return None

    @app_commands.command(name="music", description="Spotify/YouTube linki veya şarkı adıyla müzik başlat")
    @app_commands.guild_only()
    async def music(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Önce bir ses kanalına katılmalısın.", ephemeral=True)
            return
        await interaction.response.send_modal(MusicInputModal(self))

    async def handle_request(self, interaction, query, add_only=False):
        voice_channel = interaction.user.voice.channel
        guild = interaction.guild
        try:
            tracks = await asyncio.to_thread(self._resolve_query, query, interaction.user.id)
        except Exception as error:
            print(f"[MUSIC] Kaynak çözümlenemedi: {error}")
            if "open.spotify.com" in query and not self.spotify:
                return "Spotify playlisti için Render Environment Variables bölümünde SPOTIFY_CLIENT_ID ve SPOTIFY_CLIENT_SECRET tanımlı olmalı."
            if "open.spotify.com" in query:
                return "Spotify playlisti okunamadı. Playlist public olmalı ve Spotify API bilgilerini kontrol etmelisin."
            return "Bu bağlantı veya şarkı çözümlenemedi. YouTube araması ya da doğrudan bir link deneyin."
        if not tracks:
            return "Herhangi bir parça bulunamadı."
        if len(tracks) > 50:
            tracks = tracks[:50]
        state = self.states.setdefault(guild.id, MusicState())
        state.queue.extend(tracks)
        state.panel_channel_id = interaction.channel.id
        vc = guild.voice_client
        if vc and vc.channel != voice_channel:
            await vc.move_to(voice_channel)
        elif not vc:
            try:
                vc = await voice_channel.connect()
            except discord.ClientException:
                return "Ses kanalına bağlanamadım. Botun `Connect` ve `Speak` yetkilerini kontrol edin."
        if not state.playing:
            await self._play_next(guild)
        if not add_only:
            await self._send_panel(interaction.channel, state)
        return f"{len(tracks)} parça sıraya eklendi."

    def _resolve_query(self, query, user_id):
        query = query.strip()
        if "open.spotify.com" in query:
            if not self.spotify:
                raise RuntimeError("Spotify API ayarlanmamış")
            parsed = urlparse(query)
            parts = [part for part in parsed.path.split("/") if part]
            if "playlist" in parts:
                playlist_id = parts[parts.index("playlist") + 1]
                items = []
                offset = 0
                while offset < 100:
                    page = self.spotify.playlist_items(playlist_id, limit=50, offset=offset, market="TR")
                    page_items = page.get("items", [])
                    items.extend(page_items)
                    if not page.get("next") or not page_items:
                        break
                    offset += len(page_items)
                tracks = []
                for item in items:
                    track = item.get("track") or {}
                    artists = track.get("artists") or []
                    if not track.get("name") or not artists:
                        continue
                    title = f"{artists[0]['name']} - {track['name']}"
                    tracks.append(Track(title, f"ytsearch1:{title}", user_id))
                return tracks
            if "track" not in parts:
                raise RuntimeError("Geçersiz Spotify bağlantısı")
            track_id = parts[parts.index("track") + 1]
            track = self.spotify.track(track_id)
            title = f"{track['artists'][0]['name']} - {track['name']}"
            return [Track(title, f"ytsearch1:{title}", user_id)]

        source_query = query if query.startswith(("http://", "https://")) else f"ytsearch1:{query}"
        with yt_dlp.YoutubeDL({**YTDL_OPTIONS, "extract_flat": True}) as ydl:
            info = ydl.extract_info(source_query, download=False)
        entries = info.get("entries") if info.get("_type") == "playlist" else [info]
        tracks = []
        for entry in entries:
            if not entry:
                continue
            source = entry.get("webpage_url") or entry.get("url") or source_query
            if source and not source.startswith(("http://", "https://", "ytsearch")) and len(source) > 8:
                source = f"https://www.youtube.com/watch?v={source}"
            tracks.append(Track(entry.get("title", "Bilinmeyen parça"), source, user_id))
        return tracks

    async def _play_next(self, guild):
        state = self.states.get(guild.id)
        vc = guild.voice_client
        if not state or not vc or not state.queue:
            if state:
                state.playing = False
                state.current = None
            return
        state.current = state.queue.pop(0)
        state.playing = True
        state.paused = False
        try:
            source_info = await asyncio.to_thread(self._extract_audio, state.current.source)
            audio = discord.FFmpegPCMAudio(source_info["url"], **FFMPEG_OPTIONS)
        except Exception as error:
            print(f"[MUSIC] Ses kaynağı alınamadı: {error}")
            return await self._play_next(guild)

        def finished(error):
            if error:
                print(f"[MUSIC] Oynatma hatası: {error}")
            asyncio.run_coroutine_threadsafe(self._play_next(guild), self.bot.loop)

        vc.play(audio, after=finished)

    @staticmethod
    def _extract_audio(source):
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(source, download=False)
        if info.get("entries"):
            info = info["entries"][0]
        return info

    async def _send_panel(self, channel, state):
        current = state.current.title if state.current else "Sırada bekliyor"
        embed = discord.Embed(title="🎵 Müzik Paneli", description=f"**Şimdi:** {current}\n**Sıradaki:** {len(state.queue)} parça", color=discord.Color.blurple())
        embed.set_footer(text="Yeni parça eklemek veya müziği yönetmek için butonları kullan.")
        message = await channel.send(embed=embed, view=MusicPanelView(self))
        state.panel_message_id = message.id


async def setup(bot):
    await bot.add_cog(Music(bot))
