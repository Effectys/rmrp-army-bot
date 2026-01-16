import logging
import os

import discord
from discord.ext import commands

import config
from database import divisions
from database.connection import establish_db_connection
from ui.views import load_buttons
from utils.audit import audit_logger

logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("------")

    async def load_cogs(self):
        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                await self.load_extension(f"cogs.{file[:-3]}")
                logger.info(f"Loaded cog {file[:-3]}")

    async def setup_hook(self):
        await establish_db_connection()
        await divisions.load()
        audit_logger.set_bot(self)

        load_buttons(self)
        await self.load_cogs()

        await self.tree.sync()
        logger.info("Slash commands tree synced")

    async def getch_user(self, discord_id: int):
        if user := self.get_user(discord_id):
            return user
        return await self.fetch_user(discord_id)

    async def getch_member(self, discord_id: int):
        guild = self.get_guild(config.GUILD_ID)
        if member := guild.get_member(discord_id):
            return member

        try:
            return await guild.fetch_member(discord_id)
        except discord.NotFound:
            return None
