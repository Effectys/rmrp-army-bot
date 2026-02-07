import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot import Bot
from config import RANK_EMOJIS, RANKS, RankIndex
from database import divisions
from database.models import User
from utils.user_data import format_game_id, get_initiator

logger = logging.getLogger(__name__)


class Members(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def _check_permissions(self, interaction: discord.Interaction) -> User | None:
        editor_db = await get_initiator(interaction)

        if not editor_db:
            await interaction.response.send_message(
                "❌ Вы не найдены в базе данных.", ephemeral=True
            )
            return None

        MIN_RANK = RankIndex.CAPTAIN
        if (editor_db.rank or 0) < MIN_RANK:
            await interaction.response.send_message(
                f"❌ Доступ к просмотру участников подразделений доступен "
                f"со звания {RANK_EMOJIS[MIN_RANK]} {RANKS[MIN_RANK]}.",
                ephemeral=True,
            )
            return None

        return editor_db

    @app_commands.command(
        name="members", description="Просмотр участников подразделения"
    )
    @app_commands.describe(division="Подразделение для просмотра")
    @app_commands.rename(division="подразделение")
    @app_commands.choices(
        division=[
            app_commands.Choice(name=div.name, value=str(div.division_id))
            for div in divisions.divisions
        ]
    )
    async def members_handler(
        self,
        interaction: discord.Interaction,
        division: app_commands.Choice[str] | None,
    ):
        editor_db = await self._check_permissions(interaction)
        if not editor_db:
            return

        division_id = int(division.value) if division else None

        if division is None:
            if editor_db.division is not None:
                division_id = editor_db.division
            else:
                await interaction.response.send_message(
                    "❌ Вы не находитесь в подразделении. "
                    "Пожалуйста, выберите нужное подразделение для просмотра.",
                    ephemeral=True,
                )
                return

        division_info = divisions.get_division(division_id)
        if not division_info:
            await interaction.response.send_message(
                "❌ Подразделение не найдено.", ephemeral=True
            )
            return

        members = (await User.find(User.division == division_id).to_list())[:206]
        members_per_page = 25

        def member_sort_key(u: User):
            value = u.rank or 0
            if u.position:
                position = division_info.get_position_by_name(u.position)
                if position and position.privilege.value > 1:
                    value += position.privilege.value * 10
            return value

        members.sort(key=member_sort_key, reverse=True)
        members = list(enumerate(members, start=1))
        total_members = len(members)
        total_pages = max(len(members) // members_per_page, 1)

        if total_members == 0:
            await interaction.response.send_message(
                f"## {division_info.emoji} {division_info.name}: 0 участников\n\n"
                "В этом подразделении пока нет участников.",
                ephemeral=True,
            )
            return

        async def show_page(
            page_interaction: discord.Interaction, page: int, is_initial: bool = False
        ):
            start = page * members_per_page
            end = start + members_per_page

            layout = discord.ui.LayoutView(timeout=300)

            container = discord.ui.Container()
            container.add_item(
                discord.ui.TextDisplay(
                    f"## {division_info.emoji} {division_info.name}: "
                    f"{min(total_members, (page + 1) * members_per_page)}"
                    f"/{total_members} участников"
                )
            )
            container.add_item(discord.ui.Separator())

            container.add_item(
                discord.ui.TextDisplay(
                    "\n".join(
                        [
                            f"{i}. {RANK_EMOJIS[u.rank or 0]} "
                            f"`{format_game_id(u.static) if u.static else 'N // A'}`"
                            f" <@{u.discord_id}> "
                            f"❯ {u.full_name or 'Без имени'} "
                            f"❯ {u.position or 'Участник'}"
                            for i, u in members[start:end]
                        ]
                    )
                )
            )
            container.add_item(
                discord.ui.TextDisplay(f"Страница: `{page + 1}` из `{total_pages + 1}`")
            )

            container.add_item(discord.ui.Separator())

            action_row = discord.ui.ActionRow()
            prev_button = discord.ui.Button(
                emoji="⬅️",
                style=discord.ButtonStyle.gray,
                disabled=page <= 0,
            )
            prev_button.callback = lambda button_interaction: show_page(
                button_interaction, page - 1
            )
            action_row.add_item(prev_button)

            next_button = discord.ui.Button(
                emoji="➡️", style=discord.ButtonStyle.gray, disabled=page >= total_pages
            )
            next_button.callback = lambda button_interaction: show_page(
                button_interaction, page + 1
            )
            action_row.add_item(next_button)
            container.add_item(action_row)
            layout.add_item(container)

            if is_initial:
                await page_interaction.response.send_message(
                    view=layout, ephemeral=True
                )
            else:
                await page_interaction.response.edit_message(view=layout)

        await show_page(interaction, 0, is_initial=True)


async def setup(bot: Bot):
    await bot.add_cog(Members(bot))
