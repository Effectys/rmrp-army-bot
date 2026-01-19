from discord.ext import commands

import config
from bot import Bot
from ui.views.role_getting import RoleApplyView
from utils.bottom_message import update_bottom_message as _update_bottom_message

channel_id = config.CHANNELS["role_getting"]


async def update_bottom_message(bot: Bot):
    await _update_bottom_message(bot, channel_id, RoleApplyView())


class RoleGetting(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="refresh_roles")
    @commands.has_permissions(administrator=True)
    async def update_command(self, ctx: commands.Context):
        if ctx.channel.id != channel_id:
            return
        await update_bottom_message(self.bot)


async def setup(bot: Bot):
    await bot.add_cog(RoleGetting(bot))
