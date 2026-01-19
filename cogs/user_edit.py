import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
from bot import Bot
from config import RANK_EMOJIS, RANKS
from database import divisions
from database.models import User
from utils.audit import AuditAction, audit_logger
from utils.roles import to_division, to_position, to_rank
from utils.user_data import format_game_id, get_initiator

logger = logging.getLogger(__name__)


class UserEdit(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        self.edit_user = app_commands.ContextMenu(
            name="Отредактировать", callback=self.edit_user_callback
        )
        self.bot.tree.add_command(self.edit_user)

        self.fast_promotion = app_commands.ContextMenu(
            name="Повысить (+1 зв.)", callback=self.fast_promotion_callback
        )
        self.bot.tree.add_command(self.fast_promotion)

        self.dismiss_user = app_commands.ContextMenu(
            name="Уволить", callback=self.ask_dismiss_user_callback
        )
        self.bot.tree.add_command(self.dismiss_user)

    async def _check_permissions(
        self, interaction: discord.Interaction, target_user_db: User
    ) -> bool:
        editor_db = await get_initiator(interaction)

        if not editor_db:
            await interaction.response.send_message(
                "❌ Вы не найдены в базе данных.", ephemeral=True
            )
            return False

        if (editor_db.rank or 0) < 11:
            await interaction.response.send_message(
                f"❌ Доступ к управлению кадрами разрешен "
                f"со звания {RANK_EMOJIS[11]} {RANKS[11]}.",
                ephemeral=True,
            )
            return False

        if target_user_db.rank is not None:
            if (editor_db.rank or 0) <= target_user_db.rank:
                await interaction.response.send_message(
                    "❌ Вы не можете редактировать пользователей "
                    "равного или старшего звания.",
                    ephemeral=True,
                )
                return False

        return True

    async def _sync_member_discord(
        self, interaction: discord.Interaction, member: discord.Member, user_info: User
    ):
        try:
            roles = member.roles

            if user_info.division is not None:
                roles = to_division(roles, user_info.division)

            if user_info.rank is not None:
                roles = to_rank(roles, user_info.rank)

            roles = to_position(roles, user_info.division, user_info.position)

            if user_info.rank is None:
                full_name = user_info.full_name or user_info.short_name or "Неизвестный"
                new_nick = f"Уволен | {full_name}"
            else:
                new_nick = user_info.discord_nick

            new_nick = new_nick[:32]

            await member.edit(
                nick=new_nick,
                roles=roles,
                reason=f"Изменил {interaction.user.display_name}",
            )
            return True

        except discord.Forbidden:
            try:
                msg = (
                    "⚠️ Данные сохранены, но не удалось обновить Discord-профиль "
                    "(не хватает прав или иерархия ролей)."
                )
                if interaction.response.is_done():
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
            except discord.HTTPException:
                pass
            return False
        except Exception as e:
            logger.error(f"Error syncing user {member.id}: {e}")
            return False

    async def ask_dismiss_user_callback(
        self, interaction: discord.Interaction, user: discord.Member
    ):
        user_info = await User.find_one(User.discord_id == user.id)
        if not user_info:
            await interaction.response.send_message(
                "Пользователь не найден в БД.", ephemeral=True
            )
            return

        if not await self._check_permissions(interaction, user_info):
            return

        view = discord.ui.View(timeout=300)

        async def confirm_callback(btn_inter: discord.Interaction):
            old_rank = user_info.rank

            user_info.rank = None
            user_info.division = None
            user_info.position = None
            await user_info.save()

            await btn_inter.response.edit_message(
                content=f"✅ {user.mention} уволен.", view=None
            )

            try:
                member = await interaction.client.getch_member(user.id)
                await self._sync_member_discord(btn_inter, member, user_info)
            except discord.HTTPException as e:
                logger.warning(f"Failed to sync dismissed user {user.id}: {e}")

            if old_rank is not None:
                await audit_logger.log_action(
                    AuditAction.DISMISSED, interaction.user, user
                )

        confirm_button = discord.ui.Button(
            label="Подтвердить увольнение", style=discord.ButtonStyle.danger
        )
        confirm_button.callback = confirm_callback
        view.add_item(confirm_button)

        await interaction.response.send_message(
            f"Вы уверены, что хотите уволить {user.mention}?", view=view, ephemeral=True
        )

    async def fast_promotion_callback(
        self, interaction: discord.Interaction, user: discord.Member
    ):
        user_info = await User.find_one(User.discord_id == user.id)
        if not user_info:
            await interaction.response.send_message(
                "Пользователь не найден.", ephemeral=True
            )
            return

        if not await self._check_permissions(interaction, user_info):
            return

        old_rank = user_info.rank

        if user_info.rank is None:
            user_info.rank = 0
        elif user_info.rank < len(config.RANKS) - 1:
            user_info.rank += 1
        else:
            await interaction.response.send_message(
                f"⚠️ {user.mention} уже имеет максимальное звание!", ephemeral=True
            )
            return

        editor = await get_initiator(interaction)
        if (editor.rank or 0) <= user_info.rank:
            await interaction.response.send_message(
                "❌ Вы не можете присвоить звание выше или равное вашему.",
                ephemeral=True,
            )
            return

        await user_info.save()
        await self._sync_member_discord(interaction, user, user_info)

        if (old_rank or -1) < user_info.rank:
            action = AuditAction.PROMOTED
        else:
            action = AuditAction.DEMOTED

        await audit_logger.log_action(action, interaction.user, user)

        rank_name = config.RANKS[user_info.rank]
        await interaction.response.send_message(
            f"📈 {user.mention} повышен до звания **{rank_name}**.", ephemeral=True
        )

    async def edit_user_callback(
        self, interaction: discord.Interaction, user: discord.Member
    ):
        user_info = await User.find_one(User.discord_id == user.id)
        if not user_info:
            await interaction.response.send_message(
                "Пользователь не найден.", ephemeral=True
            )
            return

        if not await self._check_permissions(interaction, user_info):
            return

        view = self.build_view(user, user_info)
        await interaction.response.send_message(view=view, ephemeral=True)

    def build_view(self, user: discord.Member, user_info: User):
        layout = discord.ui.LayoutView(timeout=300)

        container = discord.ui.Container()
        container.add_item(
            discord.ui.TextDisplay(f"## Редактирование информации {user.mention}")
        )
        container.add_item(discord.ui.Separator())

        async def edit_data_callback(interaction: discord.Interaction):
            modal = discord.ui.Modal(title="Личные данные")
            name_input = discord.ui.TextInput(
                label="Имя Фамилия",
                default=user_info.full_name or "",
                max_length=50,
                required=False,
            )
            static_input = discord.ui.TextInput(
                label="Статик",
                default=str(user_info.static) if user_info.static else "",
                max_length=10,
                required=False,
            )
            modal.add_item(name_input)
            modal.add_item(static_input)

            async def data_submit(modal_inter: discord.Interaction):
                old_full_name = user_info.full_name
                old_static = user_info.static

                if name_input.value:
                    parts = name_input.value.split()
                    if len(parts) >= 2:
                        user_info.first_name = parts[0]
                        user_info.last_name = " ".join(parts[1:])
                    else:
                        user_info.first_name = name_input.value
                        user_info.last_name = ""

                if static_input.value and static_input.value.isdigit():
                    user_info.static = int(static_input.value)

                await user_info.save()

                if (
                    user_info.full_name != old_full_name
                    or user_info.static != old_static
                ):
                    await audit_logger.log_action(
                        AuditAction.NICKNAME_CHANGED, modal_inter.user, user
                    )
                    await self._sync_member_discord(modal_inter, user, user_info)

                await modal_inter.response.edit_message(
                    view=self.build_view(user, user_info)
                )

            modal.on_submit = data_submit
            await interaction.response.send_modal(modal)

        change_user_data = discord.ui.Button(emoji="📝")
        change_user_data.callback = edit_data_callback

        data_section = discord.ui.Section(accessory=change_user_data)
        data_section.add_item(discord.ui.TextDisplay("### Личные данные"))
        data_section.add_item(
            discord.ui.TextDisplay(
                f"Имя Фамилия: **{user_info.full_name or 'Не установлено'}**"
            )
        )
        data_section.add_item(
            discord.ui.TextDisplay(
                f"Статик: **`{format_game_id(user_info.static) or 'Не установлен'}`**"
            )
        )
        container.add_item(data_section)
        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay("### Звание"))
        select_rank = discord.ui.Select(
            placeholder="Изменить звание",
            options=[
                discord.SelectOption(
                    default=index == user_info.rank,
                    emoji=RANK_EMOJIS[index],
                    label=name,
                    value=str(index),
                )
                for index, name in enumerate(config.RANKS)
            ],
        )

        async def rank_callback(interaction: discord.Interaction):
            if not await self._check_permissions(interaction, user_info):
                return

            editor = await get_initiator(interaction)
            new_rank = int(select_rank.values[0])

            if (editor.rank or 0) <= new_rank:
                await interaction.response.send_message(
                    "❌ Вы не можете присвоить звание выше или равное вашему.",
                    ephemeral=True,
                )
                return

            old_rank = user_info.rank
            user_info.rank = new_rank
            await user_info.save()

            await self._sync_member_discord(interaction, user, user_info)

            if old_rank != new_rank:
                if (old_rank or -1) < new_rank:
                    action = AuditAction.PROMOTED
                else:
                    action = AuditAction.DEMOTED
                await audit_logger.log_action(action, interaction.user, user)

            await interaction.response.edit_message(
                view=self.build_view(user, user_info)
            )

        select_rank.callback = rank_callback

        rank_row = discord.ui.ActionRow()
        rank_row.add_item(select_rank)
        container.add_item(rank_row)

        async def manual_position_callback(interaction: discord.Interaction):
            change_modal = discord.ui.Modal(title="Изменение должности")
            position_input = discord.ui.TextInput(
                label="Должность",
                placeholder="Введите новую должность",
                style=discord.TextStyle.short,
                required=True,
                max_length=100,
                default=user_info.position or "",
            )
            change_modal.add_item(position_input)

            async def modal_callback(modal_interaction: discord.Interaction):
                old_position = user_info.position
                user_info.position = position_input.value
                await user_info.save()

                if old_position != user_info.position:
                    await audit_logger.log_action(
                        AuditAction.POSITION_CHANGED, modal_interaction.user, user
                    )

                await self._sync_member_discord(modal_interaction, user, user_info)

                await modal_interaction.response.edit_message(
                    view=self.build_view(user, user_info)
                )

            change_modal.on_submit = modal_callback
            await interaction.response.send_modal(change_modal)

        change_position = discord.ui.Button(emoji="📝")
        change_position.callback = manual_position_callback

        container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay("### Подразделение"))

        change_division_select = discord.ui.Select(
            placeholder="Не в подразделении...",
            options=[
                discord.SelectOption(
                    default=(user_info.division == div.division_id),
                    emoji=div.emoji,
                    label=div.name,
                    value=str(div.division_id),
                )
                for div in divisions.divisions
            ],
        )

        async def division_callback(interaction: discord.Interaction):
            if not await self._check_permissions(interaction, user_info):
                return

            new_div = int(change_division_select.values[0])
            old_div = user_info.division

            if user_info.division != new_div:
                user_info.division = new_div
                user_info.position = None
                await user_info.save()

                if old_div is None:
                    action = AuditAction.DIVISION_ASSIGNED
                else:
                    action = AuditAction.DIVISION_CHANGED
                await audit_logger.log_action(action, interaction.user, user)

                await self._sync_member_discord(interaction, user, user_info)

            await interaction.response.edit_message(
                view=self.build_view(user, user_info)
            )

        change_division_select.callback = division_callback

        division_row = discord.ui.ActionRow()
        division_row.add_item(change_division_select)
        container.add_item(division_row)

        container.add_item(discord.ui.Separator())

        position_section = discord.ui.Section(accessory=change_position)
        position_section.add_item(discord.ui.TextDisplay("### Должность"))
        container.add_item(position_section)

        div_obj = (
            divisions.get_division(user_info.division) if user_info.division else None
        )

        if div_obj and div_obj.positions:
            options = [
                discord.SelectOption(
                    default=(user_info.position == pos.name),
                    label=pos.name,
                    value=pos.name,
                )
                for pos in div_obj.positions
            ]

            if user_info.position and not any(
                [opt.value == user_info.position for opt in options]
            ):
                options.insert(
                    0,
                    discord.SelectOption(
                        label=user_info.position, value=user_info.position, default=True
                    ),
                )

            position_select = discord.ui.Select(
                placeholder="Выберите должность",
                options=options[:25],
            )

            async def position_select_callback(interaction: discord.Interaction):
                if not await self._check_permissions(interaction, user_info):
                    return

                editor = await get_initiator(interaction)
                new_position_name = position_select.values[0]

                if editor.division and editor.position:
                    editor_div_obj = divisions.get_division(editor.division)
                    if editor_div_obj and editor_div_obj.positions:
                        editor_pos_obj = next(
                            (
                                p
                                for p in editor_div_obj.positions
                                if p.name == editor.position
                            ),
                            None,
                        )
                        target_pos_obj = next(
                            (
                                p
                                for p in (div_obj.positions or [])
                                if p.name == new_position_name
                            ),
                            None,
                        )

                        if editor_pos_obj and target_pos_obj:
                            if (
                                editor_pos_obj.privilege.value
                                <= target_pos_obj.privilege.value
                            ):
                                await interaction.response.send_message(
                                    "❌ Вы не можете назначить должность "
                                    "с привилегиями выше или равными вашим.",
                                    ephemeral=True,
                                )
                                return

                old_position = user_info.position
                user_info.position = new_position_name
                await user_info.save()

                if old_position != user_info.position:
                    await audit_logger.log_action(
                        AuditAction.POSITION_CHANGED, interaction.user, user
                    )

                await self._sync_member_discord(interaction, user, user_info)

                await interaction.response.edit_message(
                    view=self.build_view(user, user_info)
                )

            position_select.callback = position_select_callback

            position_row = discord.ui.ActionRow()
            position_row.add_item(position_select)
            container.add_item(position_row)
        else:
            position_section.add_item(
                discord.ui.TextDisplay(f"_{user_info.position or 'Не установлена'}_")
            )

        layout.add_item(container)
        return layout


async def setup(bot: Bot):
    await bot.add_cog(UserEdit(bot))
