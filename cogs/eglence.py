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
            "Adamın biri gülmüş, bahçeye dikmişler.",
            "Geçen gün taksi çevirdim, hâlâ dönüyor.",
            "Matematik kitabı neden ağlıyormuş? Çok problemi varmış.",
            "Dün elektrikçiye gittim, akımı yokmuş.",
            "Kibrit çöpe ne demiş? Beni yakma.",
            "Çay içmeyene ne denir? Çay içmeyen.",
            "Hangi bağda üzüm yetişmez? Ayakkabı bağında.",
            "Bir fil diğerine ne demiş? Fil mi aradın?",
            "Fıkra anlatacaktım ama sonunu getiremedim; konu dağıldı.",
            "İki pil evlenmiş, çocukları olmuş; biri artı biri eksi.",
            "Kışın karpuz neden yenmez? Çünkü çekirdeği üşür.",
            "Dün aynaya baktım, yine aynı kişi.",
            "Kahvaltıda ne yenir? Kahvaltılık şeyler.",
            "Dün çok kitap okudum. Şimdi sayfaları benden kaçıyor.",
            "Global espri: I told my suitcase there will be no vacations this year. Now I'm dealing with emotional baggage.",
            "Global espri: Why don't scientists trust atoms? Because they make up everything.",
            "Global espri: I used to be addicted to the hokey pokey, but I turned myself around.",
            "Global espri: What do you call fake spaghetti? An impasta.",
            "Global espri: I only know 25 letters of the alphabet. I don't know Y.",
            "Global espri: Why did the bicycle fall over? It was two-tired.",
            "Global espri: Parallel lines have so much in common. It's a shame they'll never meet.",
            "Global espri: I wondered why the ball was getting bigger. Then it hit me.",
            "Seninle CSS kodlamak zor; ne zaman yaklaşsam display: none oluyorsun.",
            "React geliştiricisi neden üzgünmüş? State'ini kaybetmiş.",
            "Programcı kahveyi neden sever? Çünkü kahve yoksa exception fırlatır.",
            "SQL sorgusu bara girmiş, iki masayı join edip dönmüş.",
            "Git ile aram iyi ama branch'lerim biraz dallı budaklı.",
            "Python yılan değilmiş; sadece indentation konusunda çok hassasmış.",
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
