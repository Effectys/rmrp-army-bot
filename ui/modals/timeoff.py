import discord.ui

import config
from config import nickname_regex
from database.counters import get_next_id
from database.models import (
    RoleData,
    User,
    TimeoffRequest,
)
from ui.modals.labels import (
    name_component,
    static_label,
    period,
)
from ui.views.timeoff import ApproveTimeoffButton, RejectTimeoffButton, TimeoffCancelButton
from utils.user_data import formatted_static_to_int


class TimeoffRequestModal(discord.ui.Modal, title="Заявление на отгул"):
    name = name_component()
    period = period()

    def __init__(self, user_name: str | None):
        super().__init__()
        self.name.default = user_name

    async def on_submit(self, interaction: discord.Interaction):
        opened_request = await TimeoffRequest.find_one(
            TimeoffRequest.user_id == interaction.user.id,
            TimeoffRequest.checked == False,  # noqa: E712
        )
        if opened_request is not None:
            await interaction.response.send_message(
                "### У вас уже есть открытое заявление на рассмотрении.\n"
                "Ожидайте его рассмотрения.",
                ephemeral=True,
            )
            return

        if not nickname_regex.match(self.name.value):
            await interaction.response.send_message(
                "### Вы ввели некорректное имя и фамилию. "
                "Правильный формат: Иван Иванов.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "### Заявление отправлено на рассмотрение.", ephemeral=True
        )

        requester = await User.find_one(User.discord_id == interaction.user.id)
        static_id = requester.static
        request = TimeoffRequest(
            id=await get_next_id("timeoff_requests"),
            user_id=interaction.user.id,
            data=RoleData(full_name=self.name.value, static_id=static_id),
            period=self.period.value
        )
        await request.create()

        view = discord.ui.View(timeout=None)
        view.add_item(ApproveTimeoffButton(request_id=request.id))
        view.add_item(RejectTimeoffButton(request_id=request.id))
        view.add_item(TimeoffCancelButton(request_id=request.id))
        await interaction.channel.send(
            content=f"-# ||<@{interaction.user.id}>||",
            embed=await request.to_embed(),
            view=view,
        )

        from cogs.timeoff import update_bottom_message

        await update_bottom_message(interaction.client)
