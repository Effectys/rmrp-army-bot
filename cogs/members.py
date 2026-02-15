import logging
import math

import discord
from discord import app_commands
from discord.ext import commands

from bot import Bot
from config import RANK_EMOJIS, RANKS, RankIndex
from database import divisions
from database.models import User
from utils.user_data import format_game_id, get_initiator, display_rank

logger = logging.getLogger(__name__)


class MembersBrowser(discord.ui.LayoutView):
    def __init__(self, members: list, division_info, members_per_page: int = 25):
        super().__init__(timeout=300)
        self.members = members
        self.division_info = division_info
        self.per_page = members_per_page
        self.current_page = 0
        self.total_pages = math.ceil(len(members) / members_per_page)

        self.render_page()

    def render_page(self):
        self.clear_items()

        start = self.current_page * self.per_page
        end = start + self.per_page
        current_slice = self.members[start:end]

        header_text = (
            f"## {self.division_info.emoji} {self.division_info.name}: "
            f"{min(len(self.members), end)}/{len(self.members)} участников"
        )

        members_text = "\n".join([
            f"{i}. {RANK_EMOJIS[u.rank or 0]} "
            f"`{format_game_id(u.static) if u.static else 'N // A'}` "
            f"<@{u.discord_id}> "
            f"❯ {u.full_name or 'Без имени'} "
            f"❯ {u.position or 'Без должности'}"
            for i, u in current_slice
        ])

        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay(header_text))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(members_text))
        container.add_item(discord.ui.TextDisplay(f"Страница: `{self.current_page + 1}` из `{self.total_pages}`"))
        container.add_item(discord.ui.Separator())

        action_row = discord.ui.ActionRow()

        btn_prev = discord.ui.Button(
            emoji="⬅️",
            style=discord.ButtonStyle.gray,
            disabled=(self.current_page == 0)
        )
        btn_prev.callback = self.on_prev
        action_row.add_item(btn_prev)

        btn_next = discord.ui.Button(
            emoji="➡️",
            style=discord.ButtonStyle.gray,
            disabled=(self.current_page >= self.total_pages - 1)
        )
        btn_next.callback = self.on_next
        action_row.add_item(btn_next)

        container.add_item(action_row)

        self.add_item(container)

    async def on_prev(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_page()
            await interaction.response.edit_message(view=self)

    async def on_next(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.render_page()
            await interaction.response.edit_message(view=self)

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
                f"со звания {display_rank(MIN_RANK)}.",
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
            ] + [app_commands.Choice(name="Без подразделения", value="none")]
    )
    async def members_handler(
        self,
        interaction: discord.Interaction,
        division: app_commands.Choice[str] | None,
    ):
        editor_db = await self._check_permissions(interaction)
        if not editor_db:
            return

        if division and division.value == "none":
            members = await User.find(User.division == None).to_list()  # noqa: E711
            members.sort(key=lambda u: u.rank or 0, reverse=True)
            members_indexed = list(enumerate(members, start=1))

            class _NoDivisionInfo:
                name = "Без подразделения"
                emoji = "🚫"

                def get_position_by_name(self, _):
                    return None

            if not members:
                empty_container = discord.ui.Container()
                empty_container.add_item(
                    discord.ui.TextDisplay("## 🚫 Без подразделения: 0 участников\n\nПусто.")
                )
                view = discord.ui.LayoutView()
                view.add_item(empty_container)
                await interaction.response.send_message(view=view, ephemeral=True)
                return

            browser_view = MembersBrowser(members_indexed, _NoDivisionInfo())
            await interaction.response.send_message(view=browser_view, ephemeral=True)
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

        members = await User.find(User.division == division_id).to_list()

        def member_sort_key(u: User):
            value = u.rank or 0
            if u.position:
                position = division_info.get_position_by_name(u.position)
                if position and position.privilege.value > 1:
                    value += position.privilege.value * 10
            return value

        members.sort(key=member_sort_key, reverse=True)
        members_indexed = list(enumerate(members, start=1))

        if not members:
            empty_container = discord.ui.Container()
            empty_container.add_item(
                discord.ui.TextDisplay(f"## {division_info.emoji} {division_info.name}: 0 участников\n\nПусто."))
            view = discord.ui.LayoutView()
            view.add_item(empty_container)
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        browser_view = MembersBrowser(members_indexed, division_info)
        await interaction.response.send_message(view=browser_view, ephemeral=True)


async def setup(bot: Bot):
    await bot.add_cog(Members(bot))
