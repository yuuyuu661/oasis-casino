import os
import asyncio
import discord
import uvicorn

from discord.ext import commands
from dotenv import load_dotenv

from db import Database
from api import socket_app

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()

class CasinoBot(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents
        )

        self.db = Database()

    async def setup_hook(self):

        await self.db.connect()
        await self.db.init_db()

        await self.load_extension(
            "cogs.casino"
        )

        asyncio.create_task(
            self.start_api()
        )

    async def start_api(self):

        config = uvicorn.Config(
            socket_app,
            host="0.0.0.0",
            port=int(
                os.getenv("PORT", 8000)
            ),
            log_level="info"
        )

        server = uvicorn.Server(config)

        await server.serve()

bot = CasinoBot()

bot.run(TOKEN)
