import discord
from discord.ext import commands

import config
from bot import Bot
from database import divisions
from database.counters import get_next_id
from database.models import DismissalRequest, DismissalType, User
from ui.views.dismissal import DismissalManagementView


class AutoDismissal(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        user_db = await User.find_one(User.discord_id == member.id)

        if not user_db or user_db.rank is None:
            return

        new_id = await get_next_id("dismissal_requests")

        request = DismissalRequest(
            id=new_id,
            user_id=member.id,
            type=DismissalType.AUTO,
            full_name=user_db.full_name or member.display_name,
            static=user_db.static or 0,
            rank_index=user_db.rank,
            division_id=user_db.division,
            position=user_db.position,
            status="PENDING"
        )

        await request.create()

        channel = self.bot.get_channel(config.CHANNELS["dismissal"])

        embed = await request.to_embed(self.bot)

        user_division = divisions.get_division(user_db.division)
        if user_division and user_division.positions:
            division = user_division
        else:
            division = divisions.get_division_by_abbreviation("ВК")

        positions = division.positions if division else []
        mentions = [
            f"<@&{pos.role_id}>"
            for pos in positions
            if pos.privilege.value >= 2 and pos.role_id
        ]

        await channel.send(
            content=f"||<@{member.id}>{''.join(mentions)}||",
            embed=embed,
            view=DismissalManagementView(request.id),
        )

        from cogs.dismissal import update_bottom_message
        await update_bottom_message(self.bot)


async def setup(bot: Bot):
    await bot.add_cog(AutoDismissal(bot))