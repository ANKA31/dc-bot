import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time
import re
import asyncio
from collections import defaultdict, deque
from datetime import datetime
from utils_json import read_json, write_json

class EsikModal(discord.ui.Modal, title="Ban Eşiği Ayarla"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.sayi = discord.ui.TextInput(label="Eşik (2-20)", placeholder="Kaç mesajdan sonra banlansın?", required=True, max_length=2)
        self.add_item(self.sayi)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            sayi = int(self.sayi.value)
            if sayi < 2 or sayi > 20:
                await interaction.response.send_message("2-20 arası bir sayı girin!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Geçerli bir sayı girin!", ephemeral=True)
            return
        try:
            s = self.cog._get_guild_settings(self.guild_id)
            s["esik"] = sayi
            self.cog._save_guild_settings(self.guild_id, s)
            await self._update_message(interaction)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {e}", ephemeral=True)

    async def _update_message(self, interaction):
        try:
            s = self.cog._get_guild_settings(self.guild_id)
            embed = await self.cog._refresh_embed(s, interaction.guild)
            await interaction.response.edit_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {e}", ephemeral=True)

class KanalModal(discord.ui.Modal, title="Bildirim Kanalı Ayarla"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.kanal = discord.ui.TextInput(label="Kanal ID veya mention", placeholder="#kanal veya kanal ID'si", required=True, max_length=50)
        self.add_item(self.kanal)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        val = self.kanal.value.strip()
        kanal = None
        if val.startswith("<#") and val.endswith(">"):
            try:
                kanal = guild.get_channel(int(val[2:-1]))
            except:
                pass
        else:
            try:
                kanal = guild.get_channel(int(val))
            except ValueError:
                kanal = discord.utils.get(guild.text_channels, name=val.lstrip("#"))
        if not kanal:
            await interaction.response.send_message("Kanal bulunamadı!", ephemeral=True)
            return
        try:
            s = self.cog._get_guild_settings(self.guild_id)
            s["kanal_id"] = str(kanal.id)
            self.cog._save_guild_settings(self.guild_id, s)
            await self._update_message(interaction)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {e}", ephemeral=True)

    async def _update_message(self, interaction):
        try:
            s = self.cog._get_guild_settings(self.guild_id)
            embed = await self.cog._refresh_embed(s, interaction.guild)
            await interaction.response.edit_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {e}", ephemeral=True)

class GuvenliEkleModal(discord.ui.Modal, title="Güvenli Bot Ekle"):
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.bot_id = discord.ui.TextInput(label="Bot ID", placeholder="Eklemek istediğin botun ID'si", required=True, max_length=30)
        self.add_item(self.bot_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            s = self.cog._get_guild_settings(self.guild_id)
            bid = self.bot_id.value.strip()
            if not bid.isdigit():
                await interaction.response.send_message("Geçerli bir bot ID girin.", ephemeral=True)
                return
            member = interaction.guild.get_member(int(bid))
            if member and not member.bot:
                await interaction.response.send_message("Bu ID bir bota ait değil.", ephemeral=True)
                return
            if bid in s.get("guvenli_botlar", []):
                await interaction.response.send_message("Bu bot zaten güvenli listesinde.", ephemeral=True)
                return
            if "guvenli_botlar" not in s:
                s["guvenli_botlar"] = []
            s["guvenli_botlar"].append(bid)
            self.cog._save_guild_settings(self.guild_id, s)
            embed = discord.Embed(title="Güvenli Bot Eklendi", description=f"Bot `{bid}` güvenli listesine eklendi.", color=discord.Color.green())
            await interaction.response.edit_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"Hata: {e}", ephemeral=True)

class AntibotView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Aç/Kapat", style=discord.ButtonStyle.success, emoji="🔛")
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        s = self.cog._get_guild_settings(self.guild_id)
        s["aktif"] = not s["aktif"]
        self.cog._save_guild_settings(self.guild_id, s)
        embed = await self._build_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Eşik Ayarla", style=discord.ButtonStyle.primary, emoji="⚡")
    async def esik(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EsikModal(self.cog, self.guild_id))

    @discord.ui.button(label="Kanal Ayarla", style=discord.ButtonStyle.primary, emoji="📢")
    async def kanal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KanalModal(self.cog, self.guild_id))

    @discord.ui.button(label="Güvenli Ekle", style=discord.ButtonStyle.secondary, emoji="➕")
    async def guvenli_ekle(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GuvenliEkleModal(self.cog, self.guild_id))

    @discord.ui.button(label="Güvenli Liste", style=discord.ButtonStyle.secondary, emoji="📋")
    async def guvenli_liste(self, interaction: discord.Interaction, button: discord.ui.Button):
        s = self.cog._get_guild_settings(self.guild_id)
        guvenliler = s.get("guvenli_botlar", [])
        if not guvenliler:
            await interaction.response.send_message("Güvenli listede hiç bot yok.", ephemeral=True)
            return
        liste = "\n".join([f"• `{bid}`" for bid in guvenliler])
        embed = discord.Embed(title="Güvenli Botlar", description=liste, color=discord.Color.green())
        embed.set_footer(text=f"Toplam {len(guvenliler)} bot")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _build_embed(self, guild):
        s = self.cog._get_guild_settings(self.guild_id)
        durum = "✅ Aktif" if s["aktif"] else "❌ Devre Dışı"
        embed = discord.Embed(title="Antibot Koruması", description="Sunucuya katılan botları izler, spam durumunda otomatik banlar.", color=discord.Color.blue() if s["aktif"] else discord.Color.red())
        embed.add_field(name="Durum", value=durum, inline=True)
        embed.add_field(name="Ban Eşiği", value=f"{s['esik']} mesaj", inline=True)
        kanal = self.cog._get_kanal(s)
        embed.add_field(name="Bildirim Kanalı", value=kanal.mention if kanal else "Ayarlanmamış", inline=False)
        guvenli_sayisi = len(s.get("guvenli_botlar", []))
        embed.add_field(name="Güvenli Bot", value=f"{guvenli_sayisi} bot listede" if guvenli_sayisi else "Yok", inline=False)
        embed.set_footer(text="Butonları kullanarak ayarları değiştirebilirsin")
        return embed

    async def on_timeout(self):
        if self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except:
                pass

class Antibot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_sayac = defaultdict(deque)
        self.son_mesajlar = defaultdict(deque)
        self.kilit_lock = asyncio.Lock()
        self.join_tasks = set()
        self.settings_file = "antibot_settings.json"
        self._init_settings()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            write_json(self.settings_file, {})

    def _get_guild_settings(self, guild_id: int):
        defaults = {"aktif": False, "esik": 4, "kanal_id": None, "guvenli_botlar": [], "kilitli_kanallar": {}}
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

    def _get_kanal(self, settings):
        kanal_id = settings.get("kanal_id")
        if kanal_id:
            try:
                kanal = self.bot.get_channel(int(kanal_id))
                if kanal:
                    return kanal
            except (ValueError, TypeError):
                pass
        return None

    async def _kilitle_metinkanallari(self, guild, settings):
        """Saldırı durdurulamazsa @everyone için yazmayı kapatır."""
        me = guild.me
        if not me or not me.guild_permissions.manage_channels:
            return 0
        locked = settings.setdefault("kilitli_kanallar", {})
        changed = 0
        async with self.kilit_lock:
            for channel in guild.text_channels:
                if str(channel.id) in locked:
                    continue
                try:
                    locked[str(channel.id)] = channel.overwrites_for(guild.default_role).send_messages
                    await channel.set_permissions(guild.default_role, send_messages=False, reason="Antibot: bot uzaklaştırılamadı")
                    changed += 1
                except (discord.Forbidden, discord.HTTPException):
                    continue
            self._save_guild_settings(guild.id, settings)
        return changed

    async def _kilitleri_ac(self, guild, settings):
        locked = settings.get("kilitli_kanallar", {})
        restored = 0
        async with self.kilit_lock:
            for channel_id, previous in list(locked.items()):
                try:
                    channel = guild.get_channel(int(channel_id))
                except (TypeError, ValueError):
                    continue
                if not isinstance(channel, discord.TextChannel):
                    continue
                try:
                    await channel.set_permissions(guild.default_role, send_messages=previous, reason="Antibot: kilit yetkili tarafından açıldı")
                    restored += 1
                except (discord.Forbidden, discord.HTTPException):
                    continue
            settings["kilitli_kanallar"] = {}
            self._save_guild_settings(guild.id, settings)
        return restored

    async def _canli_uye(self, guild, member_id):
        try:
            return await guild.fetch_member(member_id)
        except discord.NotFound:
            return None
        except (discord.Forbidden, discord.HTTPException):
            return guild.get_member(member_id)

    async def _botu_ekleyen(self, guild, bot_id):
        if not guild.me or not guild.me.guild_permissions.view_audit_log:
            return None
        try:
            async for entry in guild.audit_logs(limit=10, action=discord.AuditLogAction.bot_add):
                if entry.target and entry.target.id == bot_id:
                    return entry.user
        except (discord.Forbidden, discord.HTTPException):
            pass
        return None

    async def _antibot_bildirim(self, guild, embed):
        settings = self._get_guild_settings(guild.id)
        kanal = self._get_kanal(settings) or guild.system_channel
        if not kanal:
            kanal = next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
        if kanal:
            try:
                await kanal.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                pass

    async def _mudahele_et(self, member, settings, reason):
        """Ban başarısızsa kick dener; ikisi de olmazsa acil kilit uygular."""
        try:
            await member.guild.ban(member, reason=reason, delete_message_days=1)
            return "ban"
        except (discord.Forbidden, discord.HTTPException):
            try:
                await member.guild.kick(member, reason=f"{reason} (ban başarısız)")
                return "kick"
            except (discord.Forbidden, discord.HTTPException):
                await self._kilitle_metinkanallari(member.guild, settings)
                return "kilit"

    def _spam_tespit(self, message):
        content = re.sub(r"\s+", " ", message.content.strip().lower())
        if not content:
            return False
        now = time.monotonic()
        key = (message.guild.id, message.author.id)
        recent = self.son_mesajlar[key]
        while recent and now - recent[0][0] > 10:
            recent.popleft()
        recent.append((now, content))
        same_content = sum(item == content for _, item in recent)
        return same_content >= 4 or (len(recent) >= 4 and content.startswith(("http://", "https://", "discord.gg/")))

    async def _katilim_kontrolu(self, guild_id, member_id):
        """Botu 10 saniyede dört kez banlamayı dener; kalırsa acil kilit uygular."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            settings = self._get_guild_settings(guild.id)
            if not settings["aktif"]:
                return

            for attempt in range(4):
                member = await self._canli_uye(guild, member_id)
                if not member or not member.bot:
                    return
                if str(member.id) in settings.get("guvenli_botlar", []):
                    return
                try:
                    await guild.ban(
                        member,
                        reason=f"Antibot - otomatik ban denemesi {attempt + 1}/4",
                        delete_message_days=1,
                    )
                except (discord.Forbidden, discord.HTTPException):
                    pass

                if attempt < 3:
                    await asyncio.sleep(2.5)

            member = await self._canli_uye(guild, member_id)
            if member and member.bot:
                await self._kilitle_metinkanallari(guild, settings)
                embed = discord.Embed(
                    title="Acil AntiBot Kilidi",
                    description=f"`{member}` 10 saniyede 4 ban denemesinden sonra hâlâ sunucuda kaldı.",
                    color=discord.Color.dark_red(),
                    timestamp=datetime.now(),
                )
                embed.add_field(name="Bot ID", value=f"`{member.id}`", inline=True)
                embed.add_field(name="İşlem", value="Tüm metin kanalları kilitlendi", inline=True)
                embed.set_footer(text=f"Antibot • Sunucu: {guild.name}")
                await self._antibot_bildirim(guild, embed)
        except (discord.Forbidden, discord.HTTPException):
            pass
        finally:
            self.join_tasks.discard(asyncio.current_task())

    @app_commands.command(name="antibot-kilit-ac", description="Antibotun kilitlediği metin kanallarını açar")
    @app_commands.guild_only()
    async def antibot_kilit_ac(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)
            return
        settings = self._get_guild_settings(interaction.guild.id)
        restored = await self._kilitleri_ac(interaction.guild, settings)
        await interaction.response.send_message(f"{restored} metin kanalının kilidi açıldı.", ephemeral=True)

    async def _refresh_embed(self, s, guild):
        durum = "✅ Aktif" if s["aktif"] else "❌ Devre Dışı"
        embed = discord.Embed(title="Antibot Koruması", description="Sunucuya katılan botları izler, spam durumunda otomatik banlar.", color=discord.Color.blue() if s["aktif"] else discord.Color.red())
        embed.add_field(name="Durum", value=durum, inline=True)
        embed.add_field(name="Ban Eşiği", value=f"{s['esik']} mesaj", inline=True)
        kanal = self._get_kanal(s)
        embed.add_field(name="Bildirim Kanalı", value=kanal.mention if kanal else "Ayarlanmamış", inline=False)
        guvenli_sayisi = len(s.get("guvenli_botlar", []))
        embed.add_field(name="Güvenli Bot", value=f"{guvenli_sayisi} bot listede" if guvenli_sayisi else "Yok", inline=False)
        embed.set_footer(text="Butonları kullanarak ayarları değiştirebilirsin")
        return embed

    @app_commands.command(name="antibot", description="Bot koruma sistemini yönet (butonlu menü)")
    @app_commands.guild_only()
    async def antibot(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Bu komutu kullanmak için yetkiniz yok!", ephemeral=True)
            return
        s = self._get_guild_settings(interaction.guild.id)
        durum = "✅ Aktif" if s["aktif"] else "❌ Devre Dışı"
        embed = discord.Embed(title="Antibot Koruması", description="Sunucuya katılan botları izler, spam durumunda otomatik banlar.", color=discord.Color.blue() if s["aktif"] else discord.Color.red())
        embed.add_field(name="Durum", value=durum, inline=True)
        embed.add_field(name="Ban Eşiği", value=f"{s['esik']} mesaj", inline=True)
        kanal = self._get_kanal(s)
        embed.add_field(name="Bildirim Kanalı", value=kanal.mention if kanal else "Ayarlanmamış", inline=False)
        guvenli_sayisi = len(s.get("guvenli_botlar", []))
        embed.add_field(name="Güvenli Bot", value=f"{guvenli_sayisi} bot listede" if guvenli_sayisi else "Yok", inline=False)
        embed.set_footer(text="Butonları kullanarak ayarları değiştirebilirsin")
        view = AntibotView(self, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not member.bot:
            return
        settings = self._get_guild_settings(member.guild.id)
        if not settings["aktif"]:
            return
        guvenli = str(member.id) in settings.get("guvenli_botlar", [])
        ekleyen = await self._botu_ekleyen(member.guild, member.id)

        embed = discord.Embed(
            title="Güvenli Bot Katıldı" if guvenli else "Şüpheli Bot Katıldı",
            description=f"{member.mention} (`{member.name}`) sunucuya katıldı.",
            color=discord.Color.green() if guvenli else discord.Color.red(),
            timestamp=datetime.now(),
        )
        embed.add_field(name="Bot ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="Güvenli Liste", value="✅ Evet" if guvenli else "❌ Hayır", inline=True)
        embed.add_field(name="Hesap Yaşı", value=member.created_at.strftime("%d.%m.%Y %H:%M"), inline=True)
        embed.add_field(name="Botu Ekleyen", value=ekleyen.mention if ekleyen else "Bilinmiyor", inline=True)
        roller = ", ".join(role.mention for role in member.roles if role.name != "@everyone")
        embed.add_field(name="Roller", value=roller or "Yok", inline=False)
        embed.set_footer(text=f"Antibot • Sunucu: {member.guild.name}")
        await self._antibot_bildirim(member.guild, embed)

        if not guvenli:
            task = asyncio.create_task(self._katilim_kontrolu(member.guild.id, member.id))
            self.join_tasks.add(task)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not member.bot:
            return
        settings = self._get_guild_settings(member.guild.id)
        if not settings["aktif"]:
            return
        embed = discord.Embed(
            title="Bot Sunucudan Ayrıldı",
            description=f"`{member.name}` sunucudan ayrıldı veya uzaklaştırıldı.",
            color=discord.Color.orange(),
            timestamp=datetime.now(),
        )
        embed.add_field(name="Bot ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="Botu Ekleyen", value="Ayrıntı audit kaydında", inline=True)
        embed.set_footer(text=f"Antibot • Sunucu: {member.guild.name}")
        await self._antibot_bildirim(member.guild, embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if not message.author.bot:
            return
        if message.author == self.bot.user:
            return
        settings = self._get_guild_settings(message.guild.id)
        if str(message.author.id) in settings.get("guvenli_botlar", []):
            return
        if not settings["aktif"]:
            return
        key = (message.guild.id, message.author.id)
        now = time.monotonic()
        timestamps = self.bot_sayac[key]
        while timestamps and now - timestamps[0] > 15:
            timestamps.popleft()
        timestamps.append(now)
        sayac = len(timestamps)

        if sayac == 1:
            try:
                await message.author.send(f"**{message.guild.name}** sunucusunda bot koruma aktif. {settings['esik']} mesajdan sonra otomatik banlanacaksınız.")
            except:
                pass

        if sayac >= settings["esik"] or self._spam_tespit(message):
            try:
                action = await self._mudahele_et(
                    message.author,
                    settings,
                    "Antibot - tekrarlı/link spamı tespit edildi",
                )

                kanal = self._get_kanal(settings)
                if not kanal:
                    kanal = message.guild.system_channel
                if not kanal:
                    for ch in message.guild.text_channels:
                        if ch.permissions_for(message.guild.me).send_messages:
                            kanal = ch
                            break
                if kanal:
                    title = "Bot Uzaklaştırıldı" if action != "kilit" else "Acil Kilit Uygulandı"
                    description = f"{message.author.mention} (`{message.author.name}`) için **{action}** uygulandı."
                    if action == "kilit":
                        description += " Bot uzaklaştırılamadığı için metin kanalları kilitlendi."
                    embed = discord.Embed(title=title, description=description, color=discord.Color.red(), timestamp=datetime.now())
                    embed.set_footer(text="Antibot Sistemi")
                    try:
                        await kanal.send(embed=embed)
                    except (discord.Forbidden, discord.HTTPException):
                        pass
            finally:
                self.bot_sayac.pop(key, None)
                self.son_mesajlar.pop(key, None)

async def setup(bot):
    await bot.add_cog(Antibot(bot))
