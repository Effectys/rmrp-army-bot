import discord.ui

from config import nickname_regex
from database import divisions
from database.counters import get_next_id
from database.models import ReinstatementData, ReinstatementRequest
from ui.modals.labels import name_component, screenshot_label, static_reminder
from ui.views.reinstatement import (
    ApproveReinstatementButton,
    RejectReinstatementButton,
)


class ReinstatementModal(discord.ui.Modal, title="Заявление на восстановление"):
    name = name_component()
    all_documents = screenshot_label("всех документов")
    army_pass = screenshot_label("военного билета")
    footer = static_reminder()

    def __init__(self, user_name: str):
        super().__init__()
        self.name.default = user_name

    async def on_submit(self, interaction: discord.Interaction):
        opened_request = await ReinstatementRequest.find_one(
            ReinstatementRequest.user == interaction.user.id,
            ReinstatementRequest.checked == False,  # noqa: E712
        )
        if opened_request is not None:
            await interaction.response.send_message(
                "### У вас уже есть открытое заявление на рассмотрении.\n"
                "Ожидайте его рассмотрения.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "### Заявление отправлено на рассмотрение.", ephemeral=True
        )

        if not nickname_regex.match(self.name.value):
            await interaction.response.send_message(
                "### Вы ввели некорректное имя и фамилию. "
                "Правильный формат: Иван Иванов.",
                ephemeral=True,
            )
            return

        request = ReinstatementRequest(
            id=await get_next_id("reinstatement_requests"),
            user=interaction.user.id,
            data=ReinstatementData(
                full_name=self.name.value,
                all_documents=self.all_documents.component.value,
                army_pass=self.army_pass.component.value,
            ),
        )
        await request.create()

        division = divisions.get_division_by_abbreviation("ВП")

        view = discord.ui.View()
        view.add_item(ApproveReinstatementButton(request_id=request.id))
        view.add_item(RejectReinstatementButton(request_id=request.id))
        await interaction.channel.send(
            f"-# ||<@&{division.role_id}>||", embed=await request.to_embed(), view=view
        )

        from cogs.reinstatement import update_bottom_message

        await update_bottom_message(interaction.client)
