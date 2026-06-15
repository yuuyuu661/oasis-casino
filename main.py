import os
import discord
import asyncio

from discord.ext import commands
from dotenv import load_dotenv

from db import Database

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1310885590094450739

intents = discord.Intents.default()
intents.guilds = True


class CasinoBot(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents
        )

        self.db = Database()

    async def setup_hook(self):

        print("DB接続")
        await self.db.connect()

        print("DB初期化")
        await self.db.init_db()

        print("Cog読込")
        await self.load_extension(
            "cogs.casino"
        )

        print("スラッシュ同期")

        guild = discord.Object(
            id=GUILD_ID
        )

        self.tree.copy_global_to(
            guild=guild
        )

        await self.tree.sync(
            guild=guild
        )

        print("起動完了")


bot = CasinoBot()


@bot.event
async def on_ready():

    print(
        f"LOGIN: {bot.user}"
    )


bot.run(TOKEN)