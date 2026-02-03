import datetime
import logging
import re

import discord

import config
from config import PENALTY_ROLES, INVESTIGATION_ROLE
from database.models import Blacklist, DismissalRequest, DismissalType, User
from ui.modals.dismissal import DismissalModal
from utils.audit import AuditAction, audit_logger
from utils.notifications import notify_blacklisted, notify_dismissed
from utils.user_data import format_game_id, get_initiator

logger = logging.getLogger(__name__)

closed_requests = set()


async def open_modal(interaction: discord.Interaction, d_type: DismissalType):
    user_db = await get_initiator(interaction)
    if not user_db:
        await interaction.response.send_message(
            "❌ Вас нет в базе данных.", ephemeral=True
        )
        return

    user_roles = [role.id for role in interaction.user.roles]
    if any(rid in PENALTY_ROLES for rid in user_roles) or INVESTIGATION_ROLE in user_roles:
        await interaction.response.send_message(
            "❌ Вы не можете подать рапорт на увольнение, "
            "пока у вас есть активные дисциплинарные взыскания "
            "или в отношении вас ведётся расследование.",
            ephemeral=True,
        )
        return

    full_name = user_db.full_name or ""
    await interaction.response.send_modal(DismissalModal(d_type, full_name))


async def psj_button_callback(interaction: discord.Interaction):
    user = await get_initiator(interaction)
    if not user or user.rank is None:
        await interaction.response.send_message(
            "❌ Вы не состоите на службе и не можете подать рапорт на ПСЖ.",
            ephemeral=True,
        )
        return
    await open_modal(interaction, DismissalType.PJS)


class DismissalApplyView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

    container = discord.ui.Container()
    container.add_item(discord.ui.TextDisplay("# Рапорт на увольнение"))
    container.add_item(
        discord.ui.TextDisplay(
            "### Подача рапорта\n"
            "Выберите тип увольнения, нажав соответствующую кнопку ниже.\n\n"
            "**Примечание:**\n"
            "- Если вы не отработали 5 дней во фракции, вы попадете в ЧС на 14 дней.\n"
            "- Заполняйте данные корректно, как в паспорте."
        )
    )

    container.add_item(discord.ui.Separator(visible=True))

    psj_button = discord.ui.Button(
        label="ПСЖ", style=discord.ButtonStyle.secondary, custom_id="dismissal_pjs"
    )

    psj_button.callback = psj_button_callback

    transfer_button = discord.ui.Button(
        label="Перевод",
        style=discord.ButtonStyle.primary,
        custom_id="dismissal_transfer",
    )
    transfer_button.callback = lambda interaction: open_modal(
        interaction, DismissalType.TRANSFER
    )

    action_row = discord.ui.ActionRow()
    action_row.add_item(psj_button)
    action_row.add_item(transfer_button)
    container.add_item(action_row)


class DismissalManagementButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"dismiss_(?P<action>\w+):(?P<id>\d+)",
):
    def __init__(self, action: str, request_id: int):
        labels = {"approve": "Одобрить", "reject": "Отказать"}
        styles = {
            "approve": discord.ButtonStyle.success,
            "reject": discord.ButtonStyle.danger,
        }

        super().__init__(
            discord.ui.Button(
                label=labels.get(action, action),
                style=styles.get(action, discord.ButtonStyle.secondary),
                custom_id=f"dismiss_{action}:{request_id}",
            )
        )
        self.action = action
        self.request_id = request_id

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Button,
        match: re.Match[str],
    ):
        return cls(match.group("action"), int(match.group("id")))

    async def callback(self, interaction: discord.Interaction):
        officer = await get_initiator(interaction)
        if not officer or (officer.rank or 0) < config.CAPTAIN_RANK_INDEX:
            await interaction.response.send_message(
                "❌ Доступно со звания Капитан.", ephemeral=True
            )
            return

        req = await DismissalRequest.find_one(DismissalRequest.id == self.request_id)
        if not req or req.status != "PENDING" or self.request_id in closed_requests:
            await interaction.response.send_message(
                "❌ Заявка не найдена или уже обработана.", ephemeral=True
            )
            return
        closed_requests.add(self.request_id)

        if self.action == "reject":
            req.status = "REJECTED"
            req.reviewer_id = interaction.user.id
            req.reviewed_at = datetime.datetime.now()
            await req.save()

            embed = await req.to_embed(interaction.client)
            await interaction.response.edit_message(
                content=f"<@{req.user_id}> {interaction.user.mention}",
                embed=embed,
                view=None,
            )
            return

        if self.action == "approve":
            target_user_db = await User.find_one(User.discord_id == req.user_id)
            if not target_user_db:
                closed_requests.discard(self.request_id)
                await interaction.response.send_message(
                    "❌ Пользователь не найден в БД.", ephemeral=True
                )
                return

            if (officer.rank or 0) <= (target_user_db.rank or 0):
                closed_requests.discard(self.request_id)
                await interaction.response.send_message(
                    "❌ Вы не можете уволить этого пользователя, так как его "
                    "звание выше или равно вашему.",
                    ephemeral=True,
                )
                return

            penalty_applied = False

            days_in_organization = (
                (datetime.datetime.now() - target_user_db.invited_at).days
                if target_user_db.invited_at
                else None
            )
            if (
                days_in_organization is not None
                and days_in_organization < config.PENALTY_THRESHOLD
            ):
                blacklist = Blacklist(
                    initiator=interaction.user.id,
                    reason="Неустойка",
                    evidence=interaction.message.jump_url,
                    ends_at=datetime.datetime.now() + datetime.timedelta(days=14),
                )
                target_user_db.blacklist = blacklist
                penalty_applied = True

            audit_msg = await audit_logger.log_action(
                AuditAction.DISMISSED,
                interaction.user,
                req.user_id,
                additional_info={
                    "Причина": f"[Рапорт на увольнение #{req.id}]"
                    f"({interaction.message.jump_url})"
                },
            )

            target_user_db.first_name, target_user_db.last_name = req.full_name.split(" ", 1)
            target_user_db.rank = None
            target_user_db.division = None
            target_user_db.position = None
            await target_user_db.save()

            target_member = await interaction.client.getch_member(req.user_id)
            if target_member:
                try:
                    roles_to_remove = []

                    for r_name, r_id in config.RANK_ROLES.items():
                        role = interaction.guild.get_role(r_id)
                        if role and role in target_member.roles:
                            roles_to_remove.append(role)

                    from database import divisions

                    for div in divisions.divisions:
                        role = interaction.guild.get_role(div.role_id)
                        if role and role in target_member.roles:
                            roles_to_remove.append(role)

                        for pos in div.positions:
                            if pos.role_id not in target_member.roles:
                                continue

                            pos_role = interaction.guild.get_role(pos.role_id)
                            if pos_role and pos_role in target_member.roles:
                                roles_to_remove.append(pos_role)

                    for role_enum in config.RoleId:
                        role = interaction.guild.get_role(role_enum.value)
                        if role and role in target_member.roles:
                            roles_to_remove.append(role)

                    if roles_to_remove:
                        await target_member.remove_roles(
                            *roles_to_remove, reason=f"Увольнение по рапорту #{req.id}"
                        )

                    new_nick = f"Уволен | {req.full_name}"
                    await target_member.edit(nick=new_nick[:32])
                except discord.Forbidden:
                    await interaction.followup.send(
                        "⚠️ Не удалось обновить роли/ник в Discord (нет прав).",
                        ephemeral=True,
                    )
                except Exception as e:
                    logger.error(f"Error processing dismissal discord actions: {e}")

            if penalty_applied:
                blacklist_channel = interaction.client.get_channel(
                    config.CHANNELS["blacklist"]
                )
                if blacklist_channel:
                    bl_embed = discord.Embed(
                        title="📋 Автоматический ЧС",
                        color=discord.Color.dark_red(),
                        timestamp=datetime.datetime.now(),
                    )
                    author_name = (
                        f"Составитель: {officer.full_name} | "
                        f"{format_game_id(officer.static)}"
                    )
                    bl_embed.set_author(name=author_name)
                    citizen_value = (
                        f"<@{req.user_id}> {target_user_db.full_name} | "
                        f"{format_game_id(target_user_db.static)}"
                    )
                    bl_embed.add_field(
                        name="Гражданин",
                        value=citizen_value,
                        inline=False,
                    )
                    bl_embed.add_field(
                        name="Причина",
                        value="Неустойка",
                        inline=False
                    )
                    bl_embed.add_field(
                        name="Доказательства",
                        value=f"[Перейти к логу]({audit_msg.jump_url})",
                        inline=False
                    )

                    ends_at = datetime.datetime.now() + datetime.timedelta(days=14)
                    ends_at_fmt = discord.utils.format_dt(ends_at, style="d")

                    bl_embed.add_field(
                        name="Срок", value=f"14 дней (до {ends_at_fmt})", inline=False
                    )
                    await blacklist_channel.send(
                        content=f"-# ||<@{req.user_id}> <@{officer.discord_id}>"
                        + " ".join(
                            f"<@&{mention}>" for mention in config.BLACKLIST_MENTIONS
                        )
                        + "||",
                        embed=bl_embed,
                    )

            req.status = "APPROVED"
            req.reviewer_id = interaction.user.id
            req.reviewed_at = datetime.datetime.now()
            await req.save()

            # Уведомление в ЛС об увольнении
            await notify_dismissed(
                interaction.client, req.user_id, "Увольнение по рапорту", by_report=True
            )

            # Уведомление о ЧС если применена неустойка
            if penalty_applied:
                await notify_blacklisted(
                    interaction.client, req.user_id, "Неустойка", "14 дней"
                )

            embed = await req.to_embed(interaction.client)
            if penalty_applied:
                embed.set_footer(text="Автоматически выдан ЧС за неустойку.")

            await interaction.message.edit(
                content=f"<@{req.user_id}> {interaction.user.mention}",
                embed=embed,
                view=None,
            )


class DismissalCancelButton(
    discord.ui.DynamicItem[discord.ui.Button], template=r"dismiss:cancel:(?P<id>\d+)"
):
    def __init__(self, request_id: int):
        super().__init__(
            discord.ui.Button(
                label="Отменить",
                style=discord.ButtonStyle.grey,
                custom_id=f"dismiss:cancel:{request_id}",
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
        return cls(int(match.group("id")))

    async def callback(self, interaction: discord.Interaction):
        req = await DismissalRequest.find_one(
            DismissalRequest.id == self.request_id,
            DismissalRequest.user_id == interaction.user.id,
        )
        if not req or req.status != "PENDING":
            await interaction.response.send_message(
                "❌ Заявка не найдена или уже обработана.", ephemeral=True
            )
            return

        req.status = "REJECTED"
        req.reviewer_id = interaction.user.id
        req.reviewed_at = datetime.datetime.now()
        await req.save()

        await interaction.response.send_message(
            content="✅ Ваш рапорт был отменен.", ephemeral=True
        )
        await interaction.message.delete()


class DismissalManagementView(discord.ui.View):
    def __init__(self, request_id: int):
        super().__init__(timeout=None)
        self.add_item(DismissalManagementButton("approve", request_id))
        self.add_item(DismissalManagementButton("reject", request_id))
        self.add_item(DismissalCancelButton(request_id))
