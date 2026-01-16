import discord

from database import divisions
from database.counters import get_next_id
from database.models import DismissalRequest, DismissalType, User
from ui.modals.labels import name_component


class DismissalModal(discord.ui.Modal):
    name = name_component()

    def __init__(self, dismissal_type: DismissalType, default_name: str = ""):
        super().__init__(title=f"Увольнение: {dismissal_type.value}")
        self.dismissal_type = dismissal_type
        self.name.default = default_name

    async def on_submit(self, interaction: discord.Interaction):
        user_db = await User.find_one(User.discord_id == interaction.user.id)
        if not user_db or user_db.rank is None:
            await interaction.response.send_message(
                "❌ Вы не числитесь в составе фракции.", ephemeral=True
            )
            return

        static_int = user_db.static
        if not static_int:
            await interaction.response.send_message(
                "❌ Некорректный статик.", ephemeral=True
            )
            return

        existing = await DismissalRequest.find_one(
            DismissalRequest.user_id == interaction.user.id,
            DismissalRequest.status == "PENDING",
        )
        if existing:
            await interaction.response.send_message(
                "❌ У вас уже есть активный рапорт.", ephemeral=True
            )
            return

        new_id = await get_next_id("dismissal_requests")

        request = DismissalRequest(
            id=new_id,
            user_id=interaction.user.id,
            type=self.dismissal_type,
            full_name=self.name.value,
            static=static_int,
            rank_index=user_db.rank,
            division_id=user_db.division,
            position=user_db.position,
        )
        await request.create()

        await interaction.response.send_message("✅ Рапорт подается...", ephemeral=True)

        from ui.views.dismissal import DismissalManagementView

        embed = await request.to_embed(interaction.client)
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
        await interaction.channel.send(
            content=f"||<@{interaction.user.id}>{''.join(mentions)}||",
            embed=embed,
            view=DismissalManagementView(request.id),
        )

        from cogs.dismissal import update_bottom_message

        await update_bottom_message(interaction.client)
