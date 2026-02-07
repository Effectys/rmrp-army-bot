import discord.ui
from discord import Interaction
from discord._types import ClientT

import config
from database import divisions
from database.counters import get_next_id
from database.models import Division, User
from ui.views.transfers import (
    ApproveTransferButton,
    OldApproveButton,
    RejectTransferButton,
)


class TransferModal(discord.ui.Modal):
    nickname = discord.ui.TextInput(
        label="[IC] Ваше имя и фамилия", placeholder="Иван Иванов", max_length=25
    )

    def __init__(self, destination: Division, default_nickname: str | None):
        super().__init__(title=f"Перевод в {destination.abbreviation}")
        self.destination = destination
        self.nickname.default = default_nickname

    name_age = discord.ui.TextInput(
        label="[OOC] Ваше имя и возраст",
        placeholder="Имя и возраст в реальной жизни",
    )

    timezone = discord.ui.TextInput(
        label="[OOC] Ваш часовой пояс",
        placeholder="Например: МСК, МСК+3, МСК-1",
    )

    online_prime = discord.ui.TextInput(
        label="[OOC] Ваш средний онлайн и прайм-тайм",
        placeholder="4-5 часов в день, прайм-тайм с 18:00 до 22:00 МСК",
    )

    motivation = discord.ui.TextInput(
        label="Причина выбора подразделения",
        placeholder="Почему вы хотите перевестись именно в это подразделение?",
        style=discord.TextStyle.paragraph,
    )

    async def on_submit(self, interaction: Interaction[ClientT], /) -> None:
        selected_nickname = self.nickname.value
        name_age_text = self.name_age.value
        timezone_text = self.timezone.value
        online_prime_text = self.online_prime.value
        motivation_text = self.motivation.value

        user = await User.find_one(User.discord_id == interaction.user.id)

        min_rank = (
            config.RankIndex.JUNIOR_SERGEANT
            if self.destination.abbreviation != "ССО"
            else config.RankIndex.SENIOR_SERGEANT
        )

        if user.rank < min_rank:
            return await interaction.response.send_message(
                f"### ❌ Отказано в подаче\n"
                f"В подразделение **{self.destination.abbreviation}** "
                f"можно вступить только со звания "
                f"**{config.RANKS[min_rank]}** и выше.",
                ephemeral=True,
            )

        confirmation_message = "✅ Заявление подаётся..."
        await interaction.response.send_message(confirmation_message, ephemeral=True)

        division = divisions.get_division(user.division)
        status = "OLD_DIVISION_REVIEW" if division.positions else "NEW_DIVISION_REVIEW"

        from database.models import TransferRequest

        request = TransferRequest(
            id=await get_next_id("transfer_requests"),
            user_id=interaction.user.id,
            static=user.static,
            new_division_id=self.destination.division_id,
            old_division_id=user.division,
            full_name=selected_nickname,
            name_age=name_age_text,
            timezone=timezone_text,
            online_prime=online_prime_text,
            motivation=motivation_text,
            status=status,
        )
        await request.create()

        view = discord.ui.View(timeout=None)
        if status == "NEW_DIVISION_REVIEW":
            view.add_item(
                ApproveTransferButton(
                    request_id=request.id, division_id=self.destination.division_id
                )
            )
        else:
            view.add_item(
                OldApproveButton(request_id=request.id, division_id=user.division)
            )
        view.add_item(RejectTransferButton(request_id=request.id))

        first_division = (
            divisions.get_division(request.new_division_id)
            if status == "NEW_DIVISION_REVIEW"
            else divisions.get_division(request.old_division_id)
        )
        mentions = [f"{interaction.user.mention}"] + [
            f"<@&{pos.role_id}>"
            for pos in first_division.positions
            if pos.privilege.value >= 2
        ]
        await interaction.channel.send(
            content="-# " + " ".join(mentions),
            embed=await request.to_embed(interaction.client),
            view=view,
        )

        from cogs.transfers import update_bottom_message

        await update_bottom_message(interaction.client, interaction.channel.id)
