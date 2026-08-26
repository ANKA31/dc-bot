import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import io
from utils_json import read_json, write_json
from PIL import Image, ImageDraw, ImageFont, ImageOps

class Karsilama(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "karsilama_settings.json"
        self._init_settings()

    def _init_settings(self):
        if not os.path.exists(self.settings_file):
            write_json(self.settings_file, {})

    def _get_settings(self, guild_id):
        return read_json(self.settings_file, {}).get(str(guild_id), {})

    def _save_settings(self, guild_id, settings):
        data = read_json(self.settings_file, {})
        data[str(guild_id)] = settings
        write_json(self.settings_file, data)

    async def _create_welcome_banner(self, member):
        try:
            avatar = await member.display_avatar.read()
            return await asyncio.to_thread(self._render_banner, member, avatar)
        except Exception as error:
            print(f"[KARSILAMA] Banner oluşturulamadı: {error}")
            return None

    @staticmethod
    def _render_banner(member, avatar_bytes):
        width, height = 1200, 400
        image = Image.new("RGB", (width, height), "#0b0b12")
        draw = ImageDraw.Draw(image)
        for x in range(width):
            ratio = x / width
            color = (18 + int(35 * ratio), 20 + int(22 * ratio), 48 + int(70 * ratio))
            draw.line((x, 0, x, height), fill=color)

        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGB")
        avatar = ImageOps.fit(avatar, (220, 220), method=Image.Resampling.LANCZOS)
        mask = Image.new("L", avatar.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 219, 219), fill=255)
        image.paste(avatar, (85, 90), mask)
        draw.ellipse((81, 86, 309, 314), outline="#8b5cf6", width=6)

        font_paths = [
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        bold_paths = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]

        def load_font(paths, size):
            for path in paths:
                try:
                    return ImageFont.truetype(path, size)
                except OSError:
                    continue
            return ImageFont.load_default()

        title_font = load_font(bold_paths, 54)
        name_font = load_font(bold_paths, 34)
        small_font = load_font(font_paths, 22)
        draw.text((365, 92), "ROOTx", font=title_font, fill="#c4b5fd")
        draw.text((365, 168), "Sunucumuza hoş geldin!", font=name_font, fill="#ffffff")
        draw.text((365, 224), member.display_name[:32], font=name_font, fill="#a78bfa")
        draw.text((365, 292), f"{member.guild.name[:42]}  •  #{member.guild.member_count}", font=small_font, fill="#c7c7d1")

        output = io.BytesIO()
        image.save(output, format="PNG", optimize=True)
        output.seek(0)
        return output

    @app_commands.command(name="karsilama", description="Karsilama/ayrilma mesaji ayarlari")
    @app_commands.describe(
        kanal="Mesajlarin gonderilecegi kanal",
        hosgeldin="Hos geldin mesaji ({user}, {mention}, {server}, {sayi})",
        gulegule="Gule gule mesaji ({user}, {mention}, {server}, {sayi})",
        kapat="Karşılama ve uğurlama mesajlarını kapat"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def karsilama(
        self,
        interaction: discord.Interaction,
        kanal: discord.TextChannel = None,
        hosgeldin: str = None,
        gulegule: str = None,
        kapat: bool = False
    ):
        settings = self._get_settings(interaction.guild.id)
        degisti = []

        if kapat:
            self._save_settings(interaction.guild.id, {})
            await interaction.response.send_message("Karşılama ve uğurlama mesajları kapatıldı.", ephemeral=True)
            return

        if kanal:
            settings["kanal"] = str(kanal.id)
            degisti.append(f"Kanal: {kanal.mention}")
        if hosgeldin:
            if len(hosgeldin) > 2000:
                await interaction.response.send_message("Hoş geldin mesajı 2000 karakteri geçemez.", ephemeral=True)
                return
            settings["hosgeldin"] = hosgeldin
            degisti.append("Hos geldin mesaji ayarlandi")
        if gulegule:
            if len(gulegule) > 2000:
                await interaction.response.send_message("Güle güle mesajı 2000 karakteri geçemez.", ephemeral=True)
                return
            settings["gulegule"] = gulegule
            degisti.append("Gule gule mesaji ayarlandi")

        if degisti:
            self._save_settings(interaction.guild.id, settings)

        if not settings:
            await interaction.response.send_message("Henuz ayar yapilmamis. `/karsilama kanal:#kanal hosgeldin:... gulegule:...`", ephemeral=True)
            return

        embed = discord.Embed(title="Karsilama Ayarlari", color=discord.Color.blue())
        kanal_id = settings.get("kanal")
        embed.add_field(name="Kanal", value=f"<#{kanal_id}>" if kanal_id else "Ayarlanmamis", inline=False)
        embed.add_field(name="Hos Geldin", value=settings.get("hosgeldin", "Ayarlanmamis")[:100], inline=False)
        embed.add_field(name="Gule Gule", value=settings.get("gulegule", "Ayarlanmamis")[:100], inline=False)
        embed.set_footer(text="{user}=kullanici adi {mention}=etiket {server}=sunucu {sayi}=uye sayisi {id}=kullanici ID")
        if degisti:
            embed.description = "\n".join(["✅ " + d for d in degisti])
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        settings = self._get_settings(member.guild.id)
        kanal_id = settings.get("kanal")
        mesaj = settings.get("hosgeldin", "")
        if not kanal_id:
            return
        kanal = member.guild.get_channel(int(kanal_id))
        if not isinstance(kanal, discord.TextChannel):
            return
        if mesaj:
            mesaj = mesaj.replace("{user}", member.display_name).replace("{mention}", member.mention).replace("{server}", member.guild.name).replace("{sayi}", str(member.guild.member_count)).replace("{id}", str(member.id))
        try:
            banner = await self._create_welcome_banner(member)
            if banner:
                file = discord.File(banner, filename="rootx-welcome.png")
                embed = discord.Embed(color=discord.Color(0x8B5CF6))
                embed.set_image(url="attachment://rootx-welcome.png")
                await kanal.send(content=mesaj, embed=embed, file=file, allowed_mentions=discord.AllowedMentions.none())
            elif mesaj:
                await kanal.send(mesaj, allowed_mentions=discord.AllowedMentions.none())
        except:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return
        settings = self._get_settings(member.guild.id)
        kanal_id = settings.get("kanal")
        mesaj = settings.get("gulegule", "")
        if not kanal_id or not mesaj:
            return
        kanal = member.guild.get_channel(int(kanal_id))
        if not isinstance(kanal, discord.TextChannel):
            return
        mesaj = mesaj.replace("{user}", member.display_name).replace("{mention}", member.mention).replace("{server}", member.guild.name).replace("{sayi}", str(member.guild.member_count)).replace("{id}", str(member.id))
        try:
            await kanal.send(mesaj, allowed_mentions=discord.AllowedMentions.none())
        except:
            pass

async def setup(bot):
    await bot.add_cog(Karsilama(bot))
