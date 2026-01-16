import discord.ui

import config
from database.counters import get_next_id
from database.models import (
    ExtendedRoleData,
    RoleData,
    RoleRequest,
    RoleType,
)
from ui.modals.labels import (
    name_component,
    static_label,
)
from ui.views.role_getting import ApproveRoleButton, RejectRoleButton
from utils.user_data import formatted_static_to_int


class RoleRequestModal(discord.ui.Modal, title="Заявление на получение роли"):
    name = name_component()
    static_id = static_label()
    footer = discord.ui.TextDisplay(
        "Если вы что-то не понимаете, обратитесь к военнослужащему за помощью."
    )

    def __init__(self, user_name: str | None, static_id: str | None):
        super().__init__()
        self.name.default = user_name
        self.static_id.component.default = static_id

    async def on_submit(self, interaction: discord.Interaction):
        opened_request = await RoleRequest.find_one(
            RoleRequest.user == interaction.user.id, RoleRequest.checked == False
        )
        if opened_request is not None:
            await interaction.response.send_message(
                "### У вас уже есть открытое заявление на рассмотрении.\nОжидайте его рассмотрения.",
                ephemeral=True,
            )
            return

        try:
            static_id = formatted_static_to_int(self.static_id.component.value)
        except (ValueError, TypeError):
            await interaction.response.send_message(
                "### Вы ввели некорректный статик. Правильный формат: ХХХ-ХХХ. Пример: 537-328.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "### Заявление отправлено на рассмотрение.", ephemeral=True
        )

        request = RoleRequest(
            id=await get_next_id("role_requests"),
            user=interaction.user.id,
            data=RoleData(full_name=self.name.value, static_id=static_id),
        )
        await request.create()

        view = discord.ui.View()
        view.add_item(ApproveRoleButton(request_id=request.id))
        view.add_item(RejectRoleButton(request_id=request.id))
        await interaction.channel.send(
            content=f"-# ||<@{interaction.user.id}>||",
            embed=await request.to_embed(),
            view=view,
        )

        from cogs.role_getting import update_bottom_message

        await update_bottom_message(interaction.client)


class SupplyAccessModal(discord.ui.Modal, title="Заявление на доступ к поставке"):
    name = discord.ui.TextInput(
        label="Ваше имя и фамилия", placeholder="Артём Царёв", max_length=25
    )
    static_id = discord.ui.TextInput(
        label="Ваш статик", placeholder="XXX-XXX", max_length=7
    )
    faction = discord.ui.TextInput(
        label="Ваша фракция", placeholder="ФСВНГ, МО и т.д.", max_length=50
    )
    rank_position = discord.ui.TextInput(
        label="Звание, должность",
        placeholder="Полковник, Командир роты",
        max_length=100,
    )
    certificate_link = discord.ui.TextInput(
        label="Ссылка на удостоверение",
        placeholder="https://imgur.com/...",
        max_length=200,
    )

    def __init__(self, user_name: str | None, static_id: str | None):
        super().__init__()
        self.name.default = user_name
        self.static_id.default = static_id

    async def on_submit(self, interaction: discord.Interaction):
        opened_request = await RoleRequest.find_one(
            RoleRequest.user == interaction.user.id, RoleRequest.checked == False
        )
        if opened_request is not None:
            await interaction.response.send_message(
                "### У вас уже есть открытое заявление на рассмотрении.\nОжидайте его рассмотрения.",
                ephemeral=True,
            )
            return

        try:
            static_id = formatted_static_to_int(self.static_id.value)
        except (ValueError, TypeError):
            await interaction.response.send_message(
                "### Вы ввели некорректный статик. Правильный формат: ХХХ-ХХХ. Пример: 537-328.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "### Заявление отправлено на рассмотрение.", ephemeral=True
        )

        request = RoleRequest(
            id=await get_next_id("role_requests"),
            user=interaction.user.id,
            role_type=RoleType.SUPPLY_ACCESS,
            extended_data=ExtendedRoleData(
                full_name=self.name.value,
                static_id=static_id,
                faction=self.faction.value,
                rank_position=self.rank_position.value,
                certificate_link=self.certificate_link.value,
            ),
        )
        await request.create()

        # Тегаем автора + Полковника и выше
        colonel_mentions = " ".join(
            f"<@&{role_id}>"
            for rank, role_id in config.RANK_ROLES.items()
            if config.RANKS.index(rank) >= config.RankIndex.LIEUTENANT_COLONEL
        )

        view = discord.ui.View()
        view.add_item(ApproveRoleButton(request_id=request.id))
        view.add_item(RejectRoleButton(request_id=request.id))
        await interaction.channel.send(
            content=f"-# ||<@{interaction.user.id}> {colonel_mentions}||",
            embed=await request.to_embed(),
            view=view,
        )

        from cogs.role_getting import update_bottom_message

        await update_bottom_message(interaction.client)


class GovEmployeeModal(discord.ui.Modal, title="Заявление на роль Гос. сотрудник"):
    name = discord.ui.TextInput(
        label="Ваше имя и фамилия", placeholder="Артём Царёв", max_length=25
    )
    static_id = discord.ui.TextInput(
        label="Ваш статик", placeholder="XXX-XXX", max_length=7
    )
    faction = discord.ui.TextInput(
        label="Ваша фракция", placeholder="ФСВНГ, МО и т.д.", max_length=50
    )
    rank_position = discord.ui.TextInput(
        label="Звание, должность",
        placeholder="Полковник, Командир роты",
        max_length=100,
    )
    purpose_and_certificate = discord.ui.TextInput(
        label="Цель и ссылка на удостоверение",
        placeholder="Цель: ...\nСсылка: https://imgur.com/...",
        style=discord.TextStyle.paragraph,
        max_length=500,
    )

    def __init__(self, user_name: str | None, static_id: str | None):
        super().__init__()
        self.name.default = user_name
        self.static_id.default = static_id

    async def on_submit(self, interaction: discord.Interaction):
        opened_request = await RoleRequest.find_one(
            RoleRequest.user == interaction.user.id, RoleRequest.checked == False
        )
        if opened_request is not None:
            await interaction.response.send_message(
                "### У вас уже есть открытое заявление на рассмотрении.\nОжидайте его рассмотрения.",
                ephemeral=True,
            )
            return

        try:
            static_id = formatted_static_to_int(self.static_id.value)
        except (ValueError, TypeError):
            await interaction.response.send_message(
                "### Вы ввели некорректный статик. Правильный формат: ХХХ-ХХХ. Пример: 537-328.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "### Заявление отправлено на рассмотрение.", ephemeral=True
        )

        request = RoleRequest(
            id=await get_next_id("role_requests"),
            user=interaction.user.id,
            role_type=RoleType.GOV_EMPLOYEE,
            extended_data=ExtendedRoleData(
                full_name=self.name.value,
                static_id=static_id,
                faction=self.faction.value,
                rank_position=self.rank_position.value,
                purpose=self.purpose_and_certificate.value,
            ),
        )
        await request.create()

        # Тегаем автора + Полковника и выше
        colonel_mentions = " ".join(
            f"<@&{role_id}>"
            for rank, role_id in config.RANK_ROLES.items()
            if config.RANKS.index(rank) >= config.RankIndex.COLONEL
        )

        view = discord.ui.View()
        view.add_item(ApproveRoleButton(request_id=request.id))
        view.add_item(RejectRoleButton(request_id=request.id))
        await interaction.channel.send(
            content=f"-# ||<@{interaction.user.id}> {colonel_mentions}||",
            embed=await request.to_embed(),
            view=view,
        )

        from cogs.role_getting import update_bottom_message

        await update_bottom_message(interaction.client)
