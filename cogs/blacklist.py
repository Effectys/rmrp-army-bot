import datetime

import discord
from discord import app_commands
from discord.ext import commands

import config
from bot import Bot
from database.models import Blacklist as BlacklistModel
from database.models import User
from utils.user_data import format_game_id, get_initiator

channel_id = config.CHANNELS["blacklist"]


def have_permissions(initiator: User, target: User) -> bool:
    if initiator.rank is None or initiator.rank < config.RankIndex.CAPTAIN:
        return False
    if target.rank is not None and target.rank >= initiator.rank:
        return False
    return True


class Blacklist(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(
        name="blacklist", description="Добавить военнослужащего в общий черный список"
    )
    @app_commands.rename(
        user="военнослужащий", days="дни", reason="причина", evidence="доказательства"
    )
    @app_commands.describe(
        user="Военнослужащий для добавления в черный список",
        days="Количество дней в черном списке",
        reason="Причина добавления в черный список",
        evidence="Доказательства (ссылки на скриншоты, сообщения и т.д.)",
    )
    async def blacklist(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        days: int,
        reason: str,
        evidence: str,
    ):
        db_user = await User.find_one(User.discord_id == user.id)
        initiator = await get_initiator(interaction)
        if not db_user:
            await interaction.response.send_message(
                f"Пользователь {user.mention} не найден в базе данных.", ephemeral=True
            )
            return

        if not have_permissions(initiator, db_user):
            await interaction.response.send_message(
                "❌ У вас нет прав для добавления этого пользователя в черный список.",
                ephemeral=True,
            )
            return

        blacklist = BlacklistModel(
            initiator=interaction.user.id,
            ends_at=datetime.datetime.now() + datetime.timedelta(days=days)
            if days > 0
            else None,
            reason=reason,
            evidence=evidence,
        )

        db_user.blacklist = blacklist
        await db_user.save()
        await interaction.response.send_message(
            f"Гражданин {user.mention} был добавлен в черный список.", ephemeral=True
        )

        embed = discord.Embed(
            title="📋 Новое дело",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.now(),
        )
        author_name = (
            f"Составитель: {initiator.full_name} | {format_game_id(initiator.static)}"
        )
        embed.set_author(name=author_name)
        embed.add_field(
            name="Гражданин",
            value=f"{db_user.full_name} | {format_game_id(db_user.static)}",
            inline=False,
        )
        embed.add_field(name="Причина", value=reason, inline=False)
        embed.add_field(name="Доказательства", value=evidence, inline=False)

        if days > 0:
            ends_at_fmt = discord.utils.format_dt(blacklist.ends_at, style="d")
            embed.add_field(
                name="Срок",
                value=f"{days} дней (до {ends_at_fmt})",
                inline=False,
            )
        else:
            embed.add_field(name="Срок", value="Бессрочно", inline=False)

        mentions = " ".join(f"<@&{m}>" for m in config.BLACKLIST_MENTIONS)
        await self.bot.get_channel(channel_id).send(
            f"-# ||{user.mention} {interaction.user.mention} {mentions}||",
            embed=embed,
        )

    @app_commands.command(
        name="unblacklist", description="Снять военнослужащего с черного списка"
    )
    @app_commands.rename(user="военнослужащий", reason="причина")
    @app_commands.describe(
        user="Военнослужащий для снятия с черного списка",
        reason="Причина снятия с черного списка",
    )
    async def unblacklist(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str,
    ):
        db_user = await User.find_one(User.discord_id == user.id)
        initiator = await get_initiator(interaction)

        if not db_user:
            await interaction.response.send_message(
                f"Пользователь {user.mention} не найден в базе данных.", ephemeral=True
            )
            return

        if not db_user.blacklist:
            await interaction.response.send_message(
                f"Пользователь {user.mention} не находится в черном списке.",
                ephemeral=True,
            )
            return

        if not have_permissions(initiator, db_user):
            await interaction.response.send_message(
                "У вас нет прав для снятия этого пользователя с черного списка.",
                ephemeral=True,
            )
            return

        old_blacklist = db_user.blacklist
        db_user.blacklist = None
        await db_user.save()

        await interaction.response.send_message(
            f"Гражданин {user.mention} был снят с черного списка.", ephemeral=True
        )

        embed = discord.Embed(
            title="Дело закрыто",
            color=discord.Color.dark_green(),
            timestamp=datetime.datetime.now(),
        )
        author_name = (
            f"Составитель: {initiator.full_name} | {format_game_id(initiator.static)}"
        )
        embed.set_author(name=author_name)
        embed.add_field(
            name="Гражданин",
            value=f"{db_user.full_name} | {format_game_id(db_user.static)}",
            inline=False,
        )
        embed.add_field(
            name="Изначальная причина ЧС",
            value=old_blacklist.reason,
            inline=False,
        )
        embed.add_field(name="Причина снятия", value=reason, inline=False)

        if old_blacklist.ends_at:
            embed.add_field(
                name="Оставалось",
                value=f"до {discord.utils.format_dt(old_blacklist.ends_at, style='d')}",
                inline=False,
            )
        else:
            embed.add_field(name="Срок был", value="Бессрочно", inline=False)

        await self.bot.get_channel(channel_id).send(
            f"-# ||{user.mention} {interaction.user.mention}||",
            embed=embed,
        )


async def setup(bot: Bot):
    await bot.add_cog(Blacklist(bot))
