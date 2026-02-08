import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from discord import app_commands

TOKEN = os.environ["DISCORD_TOKEN"]

intents = discord.Intents.default()
intents.message_content = True  # prefix komutları için şart

bot = commands.Bot(command_prefix="!", intents=intents)

SETTINGS = {
    "category":
    None,
    "log":
    None,
    "game_roles": [],
    "discord_roles": [],
    "panel_title":
    "🎫 Destek Sistemi",
    "panel_desc":
    "Aşağıdan destek türünü seç",
    "panel_image":
    "https://cdn.discordapp.com/attachments/1469638313471250503/1469763472584736799/file_00000000840871fdae57488b28fafa8a.png",
    "panel_thumb":
    "https://cdn.discordapp.com/attachments/1469638313471250503/1469968942096449689/Gemini_Generated_Image_qwqop7qwqop7qwqo.png"
}


# ================= MODAL =================
class PanelModal(discord.ui.Modal, title="Ticket Panel Ayarları"):
    title_input = discord.ui.TextInput(label="Panel Başlığı", max_length=100)
    desc_input = discord.ui.TextInput(label="Panel Açıklaması",
                                      style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        SETTINGS["panel_title"] = self.title_input.value
        SETTINGS["panel_desc"] = self.desc_input.value
        await interaction.response.send_message("Panel ayarlandı",
                                                ephemeral=True)


# ================= BUTTONS =================
class TicketButtons(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Talep", style=discord.ButtonStyle.secondary)
    async def talep(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        await interaction.channel.send(
            f"👤 {interaction.user.mention} ticketle ilgilenecek")
        await interaction.response.defer()

    @discord.ui.button(label="🔒 Kapat", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        await interaction.channel.delete()


# ================= TICKET SELECT =================
class TicketSelect(discord.ui.Select):

    def __init__(self):
        super().__init__(placeholder="Destek türünü seç",
                         options=[
                             discord.SelectOption(label="🎮 Oyun Destek",
                                                  value="game"),
                             discord.SelectOption(label="💬 Discord Destek",
                                                  value="discord")
                         ])

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = guild.get_channel(SETTINGS["category"])

        if self.values[0] == "game":
            roles = [
                guild.get_role(r) for r in SETTINGS["game_roles"]
                if guild.get_role(r)
            ]
            name = f"oyun-destek-{interaction.user.name}"
        else:
            roles = [
                guild.get_role(r) for r in SETTINGS["discord_roles"]
                if guild.get_role(r)
            ]
            name = f"discord-destek-{interaction.user.name}"

        overwrites = {
            guild.default_role:
            discord.PermissionOverwrite(view_channel=False),
            interaction.user:
            discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        for r in roles:
            overwrites[r] = discord.PermissionOverwrite(view_channel=True,
                                                        send_messages=True)

        channel = await guild.create_text_channel(name=name,
                                                  category=category,
                                                  overwrites=overwrites)

        await channel.send(f"{interaction.user.mention}\n" +
                           " ".join(r.mention for r in roles),
                           view=TicketButtons())

        log = guild.get_channel(SETTINGS["log"])
        if log:
            await log.send(f"📂 Ticket açıldı: {channel.mention}")

        await interaction.response.send_message("Ticket açıldı",
                                                ephemeral=True)


class TicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# ================= KURULUM SELECTLER =================
class CategorySelect(discord.ui.Select):

    def __init__(self, guild):
        super().__init__(
            placeholder="📂 Ticket kategorisi",
            options=[
                discord.SelectOption(label=c.name, value=str(c.id))
                for c in guild.categories[:25]
            ]
        )


    async def callback(self, interaction: discord.Interaction):
        SETTINGS["category"] = int(self.values[0])
        await interaction.response.defer()


class LogSelect(discord.ui.Select):

    def __init__(self, guild):
        super().__init__(
            placeholder="📜 Log kanalı",
            options=[
                discord.SelectOption(label=c.name, value=str(c.id))
                for c in guild.text_channels[:25]
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        SETTINGS["log"] = int(self.values[0])
        await interaction.response.defer()


class GameRoleSelect(discord.ui.Select):

    def __init__(self, guild):
        roles = [r for r in guild.roles if not r.is_default()]
        super().__init__(
            placeholder="🎮 Oyun destek rolleri",
            options=[
                discord.SelectOption(label=r.name, value=str(r.id))
                for r in roles[:25]
            ],
            min_values=1,
            max_values=25
        )


    async def callback(self, interaction: discord.Interaction):
        SETTINGS["game_roles"] = list(map(int, self.values))
        await interaction.response.defer()


class DiscordRoleSelect(discord.ui.Select):

    def __init__(self, guild):
        roles = [r for r in guild.roles if not r.is_default()]
        super().__init__(
            placeholder="💬 Discord destek rolleri",
            options=[
                discord.SelectOption(label=r.name, value=str(r.id))
                for r in roles[:25]
            ],
            min_values=1,
            max_values=25
        )


    async def callback(self, interaction: discord.Interaction):
        SETTINGS["discord_roles"] = list(map(int, self.values))
        await interaction.response.defer()


class TicketSetupView(discord.ui.View):

    def __init__(self, guild):
        super().__init__(timeout=300)
        self.add_item(CategorySelect(guild))
        self.add_item(LogSelect(guild))
        self.add_item(GameRoleSelect(guild))
        self.add_item(DiscordRoleSelect(guild))


# ================= EVENTS =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot hazır")


# ================= COMMANDS =================
@bot.tree.command(name="ticket-kurulum")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_kurulum(interaction: discord.Interaction):
    await interaction.response.send_message(
        "⚙️ Ticket kurulumunu aşağıdan yap",
        view=TicketSetupView(interaction.guild),
        ephemeral=True)


@bot.tree.command(name="ticket-modal")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_modal(interaction: discord.Interaction):
    await interaction.response.send_modal(PanelModal())


@bot.tree.command(name="ticket-panel")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(title=SETTINGS["panel_title"],
                          description=SETTINGS["panel_desc"],
                          color=0x2f3136)
    embed.set_image(url=SETTINGS["panel_image"])
    embed.set_thumbnail(url=SETTINGS["panel_thumb"])

    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("Panel kuruldu", ephemeral=True)


@bot.tree.command(name="ticket-add")
async def ticket_add(interaction: discord.Interaction, user: discord.Member):
    await interaction.channel.set_permissions(user,
                                              view_channel=True,
                                              send_messages=True)
    await interaction.response.send_message(f"{user.mention} ticket'e eklendi")


# ================= FLASK (REPLIT PREVIEW İÇİN) =================
app = Flask(__name__)


@app.route("/")
def home():
    return "Bot çalışıyor"


def run_flask():
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)


Thread(target=run_flask).start()

bot.run(TOKEN)

