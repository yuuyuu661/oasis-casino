import secrets

import discord

from discord.ext import commands
from discord import app_commands


# =========================
# 設定
# =========================

GUILD_ID = 1310885590094450739

ADMIN_ROLE_IDS = [
    1310906528517062770
]

CASINO_BASE_URL = (
    "https://casinotestsite-production.up.railway.app"
)


# =========================
# session生成
# =========================

def generate_session_token():

    return secrets.token_urlsafe(32)


# =========================
# View
# =========================

class CasinoPanelView(
    discord.ui.View
):

    def __init__(self, bot):

        super().__init__(
            timeout=None
        )

        self.bot = bot

    @discord.ui.button(
        label="🎰 カジノサイトへ",
        style=discord.ButtonStyle.green,
        custom_id="casino:open"
    )
    async def open_casino(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        session_token = (
            generate_session_token()
        )

        await self.bot.db.create_casino_session(
            session_token=session_token,
            user_id=str(
                interaction.user.id
            ),
            guild_id=str(
                interaction.guild.id
            )
        )

        url = (
            f"{CASINO_BASE_URL}"
            f"/?session={session_token}"
        )

        await interaction.followup.send(
            f"🎰 カジノサイトはこちら\n{url}",
            ephemeral=True
        )


# =========================
# Cog
# =========================

class CasinoCog(
    commands.Cog
):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

    async def cog_load(self):

        self.bot.add_view(
            CasinoPanelView(
                self.bot
            )
        )

    # =========================
    # パネル生成
    # =========================

    @app_commands.command(
        name="カジノパネル生成",
        description="カジノサイトパネル生成"
    )
    @app_commands.guilds(
        discord.Object(
            id=GUILD_ID
        )
    )
    async def casino_panel(
        self,
        interaction: discord.Interaction,
        title: str,
        body: str
    ):

        if not any(
            role.id in ADMIN_ROLE_IDS
            for role in interaction.user.roles
        ):

            await interaction.response.send_message(
                "権限がありません",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=title,
            description=body,
            color=discord.Color.gold()
        )

        embed.set_footer(
            text="Oasis Casino"
        )

        await interaction.response.send_message(
            embed=embed,
            view=CasinoPanelView(
                self.bot
            )
        )


async def setup(bot):

    await bot.add_cog(
        CasinoCog(bot)
    )
