import logging
import os

import discord
from discord.ext import commands
from pymongo import UpdateOne

import config
from database import divisions
from database.connection import establish_db_connection
from database.models import User
from error_handling import _custom_view_on_error, on_tree_error
from ui.views import load_buttons
from utils.audit import audit_logger
from utils.roles import get_rank_from_roles

logger = logging.getLogger(__name__)

discord.ui.View.on_error = _custom_view_on_error


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _sync_users(self):
        inited_ids = set(await User.distinct("discord_id", {"pre_inited": True}))

        guild = self.get_guild(config.GUILD_ID)

        operations = []

        for member in guild.members:
            if member.id in inited_ids:
                continue

            div, pos = divisions.get_user_data(member)
            rank = get_rank_from_roles(member.roles)

            op = UpdateOne(
                {"discord_id": member.id},
                {
                    "$set": {
                        "division": div.division_id if div else None,
                        "position": pos.name if pos else None,
                        "rank": rank,
                        "pre_inited": True,
                    },
                },
                upsert=True,
            )
            operations.append(op)

        if operations:
            await User.get_pymongo_collection().bulk_write(operations, ordered=False)
            logger.info(f"Synchronized {len(operations)} users from guild members")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("------")
        await self._sync_users()

    async def _load_cogs(self):
        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                await self.load_extension(f"cogs.{file[:-3]}")
                logger.info(f"Loaded cog {file[:-3]}")

    async def setup_hook(self):
        await establish_db_connection()
        await divisions.load()
        audit_logger.set_bot(self)

        load_buttons(self)
        await self._load_cogs()

        self.tree.on_error = on_tree_error

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
