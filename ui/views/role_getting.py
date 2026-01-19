import datetime
import re
from typing import Any

import discord
from discord import Interaction, InteractionResponse
from discord._types import ClientT

import config
import texts
from database import divisions
from database.models import RoleRequest, RoleType, User
from ui.views.indicators import indicator_view
from utils.audit import AuditAction, audit_logger
from utils.user_data import format_game_id, update_user_name_if_changed, get_initiator

closed_requests = set()


async def _get_user_defaults(interaction: discord.Interaction):
    """Получить данные пользователя для заполнения формы."""
    user = await get_initiator(interaction)
    user_name, static_id = None, None
    if user:
        if user.full_name:
            user_name = user.full_name
        if user.static:
            static_id = format_game_id(user.static)
    return user, user_name, static_id


async def _check_can_apply(interaction: discord.Interaction) -> bool:
    """Проверить, может ли пользователь подать заявку."""
    opened_request = await RoleRequest.find_one(
        RoleRequest.user == interaction.user.id,
        RoleRequest.checked == False,  # noqa: E712
    )
    if opened_request is not None:
        await interaction.response.send_message(
            "### У вас уже есть открытое заявление на рассмотрении.\n"
            "Ожидайте его рассмотрения.",
            ephemeral=True,
        )
        return False

    user = await get_initiator(interaction)
    if user and user.blacklist:
        await interaction.response.send_message(
            "### Вы не можете подать заявление на роль, "
            "так как на вас наложен черный список.\n"
            f"Дата окончания: {discord.utils.format_dt(user.blacklist.ends_at, 'd')}.",
            ephemeral=True,
        )
        return False
    return True


async def army_button_callback(interaction: discord.Interaction):
    """Callback для кнопки ВС РФ."""
    if not await _check_can_apply(interaction):
        return

    _, user_name, static_id = await _get_user_defaults(interaction)

    from ui.modals.role_getting import RoleRequestModal

    await interaction.response.send_modal(
        RoleRequestModal(user_name=user_name, static_id=static_id)
    )


async def supply_access_button_callback(interaction: discord.Interaction):
    """Callback для кнопки Доступ к поставке."""
    if not await _check_can_apply(interaction):
        return

    _, user_name, static_id = await _get_user_defaults(interaction)

    from ui.modals.role_getting import SupplyAccessModal

    await interaction.response.send_modal(
        SupplyAccessModal(user_name=user_name, static_id=static_id)
    )


async def gov_employee_button_callback(interaction: discord.Interaction):
    """Callback для кнопки Гос. сотрудник."""
    if not await _check_can_apply(interaction):
        return

    _, user_name, static_id = await _get_user_defaults(interaction)

    from ui.modals.role_getting import GovEmployeeModal

    await interaction.response.send_modal(
        GovEmployeeModal(user_name=user_name, static_id=static_id)
    )


class RoleApplyView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

    container = discord.ui.Container()
    container.add_item(discord.ui.TextDisplay(texts.role_title))
    container.add_item(discord.ui.TextDisplay(texts.role_submission))
    container.add_item(discord.ui.TextDisplay(texts.role_requirements))

    container.add_item(discord.ui.Separator(visible=True))

    # Кнопка ВС РФ
    army_button = discord.ui.Button(
        label="ВС РФ",
        emoji="🎖️",
        style=discord.ButtonStyle.primary,
        custom_id="role_apply_army",
    )
    army_button.callback = army_button_callback

    # Кнопка Доступ к поставке
    supply_button = discord.ui.Button(
        label="Доступ к поставке",
        emoji="📦",
        style=discord.ButtonStyle.secondary,
        custom_id="role_apply_supply",
    )
    supply_button.callback = supply_access_button_callback

    # Кнопка Гос. сотрудник
    gov_button = discord.ui.Button(
        label="Гос. сотрудник",
        emoji="🏛️",
        style=discord.ButtonStyle.secondary,
        custom_id="role_apply_gov",
    )
    gov_button.callback = gov_employee_button_callback

    action_row = discord.ui.ActionRow()
    action_row.add_item(army_button)
    action_row.add_item(supply_button)
    action_row.add_item(gov_button)
    container.add_item(action_row)


def get_required_rank(role_type: RoleType) -> int:
    """Получить минимальное звание для одобрения заявки."""
    ranks = {
        RoleType.ARMY: config.RankIndex.JUNIOR_LIEUTENANT,
        RoleType.SUPPLY_ACCESS: config.RankIndex.LIEUTENANT_COLONEL,
        RoleType.GOV_EMPLOYEE: config.RankIndex.COLONEL,
    }
    return ranks.get(role_type, config.RankIndex.COLONEL)


async def check_approve_permission(
    interaction: Interaction[ClientT], request: RoleRequest
) -> bool:
    """Проверить права на одобрение заявки в зависимости от типа."""
    user = await get_initiator(interaction)
    if not user:
        return False

    required_rank = get_required_rank(request.role_type)

    # Проверка по званию
    if (user.rank or 0) >= required_rank:
        return True

    # Для ВС РФ - дополнительная проверка по подразделению
    if request.role_type == RoleType.ARMY:
        division = divisions.get_division(user.division)
        if not division:
            return False
        if division.abbreviation == "ВК":
            return True
        if division.positions:
            for position in division.positions:
                if position.name == user.position and position.privilege.value >= 3:
                    return True

    return False


class ApproveRoleButton(
    discord.ui.DynamicItem[discord.ui.Button], template=r"approve_role:(?P<id>\d+)"
):
    def __init__(self, request_id: int):
        super().__init__(
            discord.ui.Button(
                label="Одобрить",
                emoji="👍",
                custom_id=f"approve_role:{request_id}",
                style=discord.ButtonStyle.success,
            )
        )
        self.request_id = request_id

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Button,
        match: re.Match[str],
    ):
        request_id = int(match.group("id"))
        return cls(request_id)

    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        request = await RoleRequest.find_one(RoleRequest.id == self.request_id)
        if not request:
            await interaction.response.send_message("Запрос не найден.", ephemeral=True)
            return

        if request.checked or self.request_id in closed_requests:
            await interaction.response.send_message(
                "Этот запрос уже был обработан.", ephemeral=True
            )
            return
        closed_requests.add(self.request_id)

        # Проверка прав
        if not await check_approve_permission(interaction, request):
            closed_requests.discard(self.request_id)
            role_names = {
                RoleType.ARMY: "Младший лейтенант",
                RoleType.SUPPLY_ACCESS: "Подполковник",
                RoleType.GOV_EMPLOYEE: "Полковник",
            }
            required = role_names.get(request.role_type, "Полковник")
            await interaction.response.send_message(
                f"У вас нет прав для одобрения этой заявки. "
                f"Требуется звание: {required}+",
                ephemeral=True,
            )
            return

        request.approved = True
        request.checked = True
        await request.save()
        assert isinstance(interaction.response, InteractionResponse)
        await interaction.response.edit_message(
            content=f"-# ||<@{request.user}> {interaction.user.mention}||",
            embed=await request.to_embed(),
            view=indicator_view(f"Одобрил {interaction.user.display_name}", emoji="👍"),
        )

        user_discord = await interaction.client.getch_member(request.user)

        if request.role_type == RoleType.ARMY:
            # Логика для ВС РФ
            user = await User.find_one(User.discord_id == request.user)
            if not user:
                user = User(discord_id=request.user)
            user.rank = 0
            user.division = 1
            user.first_name, user.last_name = request.data.full_name.split(" ", 1)
            user.static = request.data.static_id
            user.invited_at = datetime.datetime.now()
            user.pre_inited = True
            await user.save()

            # Роли: Военнослужащий, Рядовой, Военная академия
            role_ids = [
                config.RoleId.MILITARY.value,
                config.RANK_ROLES[config.RANKS[0]],
                config.RoleId.MILITARY_ACADEMY.value,
            ]
            roles_to_add = [interaction.guild.get_role(role_id) for role_id in role_ids]
            new_roles = [
                role for role in user_discord.roles if role.id not in role_ids
            ] + [role for role in roles_to_add if role is not None]
            await user_discord.edit(
                nick=user.discord_nick,
                roles=new_roles,
                reason=f"Одобрено получение роли ВС РФ by {interaction.user.id}",
            )

            await audit_logger.log_action(
                action=AuditAction.INVITED,
                initiator=interaction.user,
                target=user.discord_id,
            )

        elif request.role_type == RoleType.SUPPLY_ACCESS:
            # Логика для Доступ к поставке
            user = await User.find_one(User.discord_id == request.user)
            if not user:
                user = User(discord_id=request.user)
                await user.save()
            await update_user_name_if_changed(
                user, request.extended_data.full_name, interaction.user
            )

            role = interaction.guild.get_role(config.RoleId.SUPPLY_ACCESS.value)
            new_roles = list(user_discord.roles)
            if role:
                new_roles.append(role)
            # Ник: Фракция | Имя Фамилия
            new_nick = (
                f"{request.extended_data.faction} | {request.extended_data.full_name}"[
                    :32
                ]
            )
            await user_discord.edit(
                nick=new_nick,
                roles=new_roles,
                reason=f"Одобрено роль Доступ к поставке by {interaction.user.id}",
            )

        elif request.role_type == RoleType.GOV_EMPLOYEE:
            # Логика для Гос. сотрудник
            user = await User.find_one(User.discord_id == request.user)
            if not user:
                user = User(discord_id=request.user)
                await user.save()
            await update_user_name_if_changed(
                user, request.extended_data.full_name, interaction.user
            )

            role = interaction.guild.get_role(config.RoleId.GOV_EMPLOYEE.value)
            new_roles = list(user_discord.roles)
            if role:
                new_roles.append(role)
            # Ник: Фракция | Имя Фамилия
            new_nick = (
                f"{request.extended_data.faction} | {request.extended_data.full_name}"[
                    :32
                ]
            )
            await user_discord.edit(
                nick=new_nick,
                roles=new_roles,
                reason=f"Одобрено роль Гос. сотрудник by {interaction.user.id}",
            )


class RejectRoleButton(
    discord.ui.DynamicItem[discord.ui.Button], template=r"reject_role:(?P<id>\d+)"
):
    def __init__(self, request_id: int):
        super().__init__(
            discord.ui.Button(
                label="Отклонить",
                emoji="👎",
                custom_id=f"reject_role:{request_id}",
                style=discord.ButtonStyle.danger,
            )
        )
        self.request_id = request_id

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Button,
        match: re.Match[str],
    ):
        request_id = int(match.group("id"))
        return cls(request_id)

    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        request = await RoleRequest.find_one(RoleRequest.id == self.request_id)
        if not request:
            await interaction.response.send_message("Запрос не найден.", ephemeral=True)
            return

        # Двойная проверка: БД (персистентная) + in-memory (быстрая)
        if request.checked or self.request_id in closed_requests:
            await interaction.response.send_message(
                "Этот запрос уже был обработан.", ephemeral=True
            )
            return
        closed_requests.add(self.request_id)

        # Проверка прав
        if not await check_approve_permission(interaction, request):
            closed_requests.discard(self.request_id)
            role_names = {
                RoleType.ARMY: "Младший лейтенант",
                RoleType.SUPPLY_ACCESS: "Подполковник",
                RoleType.GOV_EMPLOYEE: "Полковник",
            }
            required = role_names.get(request.role_type, "Полковник")
            await interaction.response.send_message(
                f"У вас нет прав для отклонения этой заявки. "
                f"Требуется звание: {required}+",
                ephemeral=True,
            )
            return

        request.approved = False
        request.checked = True
        await request.save()
        assert isinstance(interaction.response, InteractionResponse)
        await interaction.response.edit_message(
            content=f"-# ||<@{request.user}> {interaction.user.mention}||",
            embed=await request.to_embed(),
            view=indicator_view(
                f"Отклонил {interaction.user.display_name}", emoji="👎"
            ),
        )
