import discord
from discord.ext import commands
from discord import app_commands
import re
import json
import os
import time
from collections import defaultdict, deque
from datetime import timedelta, datetime
from utils_json import read_json, write_json

class SpamSureModal(discord.ui.Modal, title="Spam Susturma Süresi"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.sure = discord.ui.TextInput(label="Süre (dakika, 1-40320)", placeholder="Örn: 5", required=True, max_length=5)
        self.add_item(self.sure)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            dakika = int(self.sure.value)
            if dakika < 1 or dakika > 40320:
                await interaction.response.send_message("1-40320 arası girin!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Geçerli bir sayı girin!", ephemeral=True)
            return
        s = self.cog._get_guild_settings(self.guild_id)
        s["spam_mute_duration"] = dakika
        self.cog._save_guild_settings(self.guild_id, s)
        await self._refresh(interaction)

    async def _refresh(self, interaction):
        s = self.cog._get_guild_settings(self.guild_id)
        is_spam_panel = interaction.message and interaction.message.embeds and interaction.message.embeds[0].title == "Spam Kalkanı"
        embed = self.cog._build_spam_embed(s) if is_spam_panel else self.cog._build_embed(s)
        await interaction.response.edit_message(embed=embed)

class OtoKorumaView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Bu menüyü kullanmak için yetkiniz yok!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Link Filtresi", style=discord.ButtonStyle.primary, emoji="🔗")
    async def link_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        s = self.cog._get_guild_settings(self.guild_id)
        s["link_filter"] = not s["link_filter"]
        self.cog._save_guild_settings(self.guild_id, s)
        embed = self.cog._build_embed(s)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Spam Filtresi", style=discord.ButtonStyle.primary, emoji="⚠️")
    async def spam_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        s = self.cog._get_guild_settings(self.guild_id)
        s["spam_filter"] = not s["spam_filter"]
        self.cog._save_guild_settings(self.guild_id, s)
        embed = self.cog._build_embed(s)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Spam Süre", style=discord.ButtonStyle.secondary, emoji="⏱️")
    async def spam_sure(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SpamSureModal(self.cog, self.guild_id))

    async def on_timeout(self):
        if self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except:
                pass

class SpamKalkanView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Bu menüyü kullanmak için yetkiniz yok!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Spam Kalkanı", style=discord.ButtonStyle.success, emoji="🛡️")
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = self.cog._get_guild_settings(self.guild_id)
        settings["spam_filter"] = not settings.get("spam_filter", True)
        self.cog._save_guild_settings(self.guild_id, settings)
        await interaction.response.edit_message(embed=self.cog._build_spam_embed(settings), view=self)

    @discord.ui.button(label="Süre Ayarla", style=discord.ButtonStyle.primary, emoji="⏱️")
    async def duration(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SpamSureModal(self.cog, self.guild_id))

    @discord.ui.button(label="Acil Kilit", style=discord.ButtonStyle.danger, emoji="🔒")
    async def emergency(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = self.cog._get_guild_settings(self.guild_id)
        settings["emergency_lock"] = not settings.get("emergency_lock", True)
        self.cog._save_guild_settings(self.guild_id, settings)
        await interaction.response.edit_message(embed=self.cog._build_spam_embed(settings), view=self)

    async def on_timeout(self):
        if self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except:
                pass

class Otomoderasyon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "autmod_settings.json"
        self._init_settings()
        self.link_pattern = re.compile(r'https?://[^\s]+|www\.[^\s]+')
        self.mesaj_izleme = defaultdict(deque)
        self.spam_ihlalleri = defaultdict(deque)

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            write_json(self.settings_file, {})

    def _get_guild_settings(self, guild_id: int):
        defaults = {"link_filter": False, "spam_filter": True, "spam_mute_duration": 5, "emergency_lock": True}
        settings = read_json(self.settings_file, {})
        gid = str(guild_id)
        if gid not in settings:
            settings[gid] = defaults
        else:
            for k, v in defaults.items():
                settings[gid].setdefault(k, v)
        return settings[gid]

    def _save_guild_settings(self, guild_id: int, settings: dict):
        all_settings = read_json(self.settings_file, {})
        all_settings[str(guild_id)] = settings
        write_json(self.settings_file, all_settings)

    def _build_embed(self, s):
        embed = discord.Embed(title="Oto Koruma Sistemi", description="Link ve spam filtrelerini butonlarla yönetebilirsin.", color=discord.Color.blue())
        link_durum = "✅ Açık" if s.get("link_filter", False) else "❌ Kapalı"
        spam_durum = "✅ Açık" if s.get("spam_filter", False) else "❌ Kapalı"
        embed.add_field(name="🔗 Link Filtresi", value=link_durum, inline=True)
        embed.add_field(name="⚠️ Spam Filtresi", value=spam_durum, inline=True)
        embed.add_field(name="⏱️ Spam Süre", value=f"{s.get('spam_mute_duration', 5)} dk", inline=True)
        embed.set_footer(text="Her filtreyi açıp/kapatmak için butonlara tıkla")
        return embed

    def _build_spam_embed(self, s):
        embed = discord.Embed(
            title="Spam Kalkanı",
            description="Normal hesaplardan gelen hızlı ve tekrarlı spamı otomatik durdurur.",
            color=discord.Color.green() if s.get("spam_filter", True) else discord.Color.red(),
        )
        embed.add_field(name="Durum", value="✅ Aktif" if s.get("spam_filter", True) else "❌ Kapalı", inline=True)
        embed.add_field(name="Timeout Süresi", value=f"{s.get('spam_mute_duration', 5)} dakika", inline=True)
        embed.add_field(name="Acil Kanal Kilidi", value="✅ Aktif" if s.get("emergency_lock", True) else "❌ Kapalı", inline=True)
        embed.add_field(name="Tespit", value="5 saniyede 4 mesaj veya aynı mesajın 3 tekrarı", inline=False)
        embed.set_footer(text="Ayarları aşağıdaki butonlardan yönetebilirsin")
        return embed

    @app_commands.command(name="antispam", description="Normal hesaplar için spam kalkanını yönet")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def antispam(self, interaction: discord.Interaction):
        settings = self._get_guild_settings(interaction.guild.id)
        view = SpamKalkanView(self, interaction.guild.id)
        await interaction.response.send_message(embed=self._build_spam_embed(settings), view=view)
        view.message = await interaction.original_response()

    @app_commands.command(name="otokoruma", description="Oto-koruma (link/spam filtrelerini) yönet")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def otokoruma(self, interaction: discord.Interaction):
        s = self._get_guild_settings(interaction.guild.id)
        embed = self._build_embed(s)
        view = OtoKorumaView(self, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if message.author == self.bot.user:
            return
        if message.author.guild_permissions.administrator:
            return

        yetki = message.guild.me.guild_permissions
        settings = self._get_guild_settings(message.guild.id)

        if not message.author.bot and settings.get("link_filter", False):
            if self.link_pattern.search(message.content) and yetki.manage_messages:
                try:
                    await message.delete()
                    await message.author.send(f"Bu kanalda link göndermek yasak! Kanal: {message.channel.mention}")
                except:
                    pass

        if not message.author.bot and settings.get("spam_filter", False):
            now = time.monotonic()
            key = (message.guild.id, message.author.id)
            content = re.sub(r"\s+", " ", message.content.strip().lower())
            history = self.mesaj_izleme[key]
            while history and now - history[0][0] > 5:
                history.popleft()
            history.append((now, content))
            repeated = content and sum(item == content for _, item in history) >= 3
            rapid = len(history) >= 4

            if repeated or rapid:
                violation_times = self.spam_ihlalleri[key]
                while violation_times and now - violation_times[0] > 300:
                    violation_times.popleft()
                violation_times.append(now)
                mute_dk = min(settings.get("spam_mute_duration", 5) * max(1, len(violation_times)), 40320)

                if yetki.manage_messages:
                    try:
                        await message.delete(reason="Oto-koruma: spam")
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                if yetki.moderate_members:
                    try:
                        await message.author.timeout(timedelta(minutes=mute_dk), reason="Oto-koruma: hızlı/tekrarlı spam")
                        await message.author.send(f"{mute_dk} dakika susturuldunuz: hızlı veya tekrarlı spam.")
                    except (discord.Forbidden, discord.HTTPException):
                        pass

                # Çok sayıda mesajda moderasyon yetkisi yetersizse ortak acil kilit devreye girer.
                if (len(violation_times) >= 2 and not yetki.moderate_members
                        and settings.get("emergency_lock", True)):
                    antibot = self.bot.get_cog("Antibot")
                    if antibot:
                        await antibot.acil_kilit(message.guild, "Oto-koruma: ağır kullanıcı spamı")
                history.clear()

async def setup(bot):
    await bot.add_cog(Otomoderasyon(bot))
