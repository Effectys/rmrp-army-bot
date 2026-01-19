from discord.ext import commands

import config
from bot import Bot
from ui.views import ReinstatementApplyView
from utils.bottom_message import update_bottom_message as _update_bottom_message

channel_id = config.CHANNELS["reinstatement"]


async def update_bottom_message(bot: Bot):
    await _update_bottom_message(bot, channel_id, ReinstatementApplyView())


class Reinstatement(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="upd")
    @commands.has_permissions(administrator=True)
    async def update_command(self, ctx: commands.Context):
        if ctx.channel.id != channel_id:
            return
        await update_bottom_message(self.bot)


async def setup(bot: Bot):
    await bot.add_cog(Reinstatement(bot))
