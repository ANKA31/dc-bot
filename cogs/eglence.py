import discord
from discord.ext import commands
from discord import app_commands
import random

class Eglence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="yazi-tura", description="Yazi veya tura at")
    async def yazi_tura(self, interaction: discord.Interaction):
        sonuc = random.choice(["Yazı", "Tura"])
        embed = discord.Embed(title="🪙 Yazı Tura", description=f"**{sonuc}**!", color=discord.Color.gold())
        embed.set_footer(text=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="zar", description="Zar at (1-6)")
    async def zar(self, interaction: discord.Interaction):
        sonuc = random.randint(1, 6)
        zar_emojileri = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
        embed = discord.Embed(title="🎲 Zar Atıldı", description=f"{zar_emojileri[sonuc]} **{sonuc}**", color=discord.Color.blue())
        embed.set_footer(text=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="espri", description="Türkçe ve global esprilerden rastgele birini gösterir")
    async def espri(self, interaction: discord.Interaction):
        espriler = [
            "Seninle CSS kodlamak zor; ne zaman yaklaşsam display: none oluyorsun.",
            "React geliştiricisi neden üzgünmüş? State'ini kaybetmiş.",
            "Programcı kahveyi neden sever? Çünkü kahve yoksa exception fırlatır.",
            "SQL sorgusu bara girmiş, iki masayı join edip dönmüş.",
            "Git ile aram iyi ama branch'lerim biraz dallı budaklı.",
            "Python yılan değilmiş; sadece indentation konusunda çok hassasmış.",
            "Bugün çok üretkendim. Üretkenlik uygulamasını açıp kapattım.",
            "Bilgisayarım çok soğuk. Pencereleri açık kalmış.",
            "Klavye neden doktora gitmiş? Tuşları ağrıyormuş.",
            "Wi-Fi şifresini sordum, 'önce çalış' dedi.",
            "Türk kahvesi neden kod yazamaz? Her satırın sonunda telvesi kalır.",
            "Temel Reis ıspanağı neden seviyormuş? Çünkü spinach ile güçleniyormuş.",
            "Dün elektrikçiye gittim, akımı yokmuş.",
            "Matematik kitabı neden ağlıyormuş? Çok problemi varmış.",
            "Adamın biri gülmüş, bahçeye dikmişler.",
            "Geçen gün taksi çevirdim, hâlâ dönüyor.",
            "Fıkra anlatacaktım ama sonunu getiremedim; konu dağıldı.",
            "Bir dosya diğerine ne demiş? Uzantımızı koparmayalım.",
            "JavaScript neden terapiste gitmiş? Çok fazla callback'i varmış.",
            "Bir HTTP isteği bara girmiş: 'Bana bir 200 ver.' demiş.",
        ]
        embed = discord.Embed(title="😂 Espri", description=random.choice(espriler), color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Kullanıcının avatarını göster")
    @app_commands.describe(kullanici="Avatarı gösterilecek kullanıcı (opsiyonel)")
    async def avatar(self, interaction: discord.Interaction, kullanici: discord.User = None):
        hedef = kullanici or interaction.user
        if not hedef.avatar:
            await interaction.response.send_message("Bu kullanıcının avatarı yok.", ephemeral=True)
            return
        embed = discord.Embed(title=f"{hedef.name} Avatarı", color=discord.Color.blue())
        embed.set_image(url=hedef.avatar.url)
        embed.set_footer(text=f"ID: {hedef.id}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ping", description="Bot gecikmesini göster")
    async def ping(self, interaction: discord.Interaction):
        gecikme = round(self.bot.latency * 1000)
        renk = discord.Color.green() if gecikme < 100 else discord.Color.orange() if gecikme < 200 else discord.Color.red()
        embed = discord.Embed(title="🏓 Pong!", description=f"Gecikme: **{gecikme}ms**", color=renk)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Eglence(bot))
