import discord
from discord.ext import commands

import config
from bot import Bot
from ui.views.supplies import SupplyCreateView
from utils.bottom_message import update_bottom_message as _update_bottom_message

channel_id = config.CHANNELS["storage_requests"]


async def update_bottom_message(bot: Bot):
    embed = discord.Embed(
        title="📦 Склад",
        description=f"Нажмите кнопку ниже, чтобы сформировать заявку на получение амуниции и материалов.\n\n"
        f"**Требования:** Звание Старший Сержант и выше.\n"
        f"**Лимиты:** Соблюдайте установленные лимиты: {config.SUPPLY_INFO_LINK}",
        color=discord.Color.blue(),
    )
    await _update_bottom_message(bot, channel_id, SupplyCreateView(), embed)


class Supplies(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="upds")
    @commands.has_permissions(administrator=True)
    async def update_command(self, ctx: commands.Context):
        if ctx.channel.id != channel_id:
            return
        await update_bottom_message(self.bot)


async def setup(bot: Bot):
    await bot.add_cog(Supplies(bot))
