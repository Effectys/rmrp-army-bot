import discord

import config
import texts
from database.models import User
from ui.modals.supplies_audit import ClearSupplyModal, GiveSupplyModal
from utils.user_data import needs_static_input, get_initiator


async def give_button_callback(interaction: discord.Interaction):
    user = await get_initiator(interaction)

    if not user or (user.rank or 0) < config.RankIndex.MAJOR:
        await interaction.response.send_message(
            "❌ Доступно со звания Майор.", ephemeral=True
        )
        return

    await interaction.response.send_modal(GiveSupplyModal())


async def clear_button_callback(interaction: discord.Interaction):
    user = await get_initiator(interaction)

    if not user or (user.rank or 0) < config.RankIndex.MAJOR:
        await interaction.response.send_message(
            "❌ Доступно со звания Майор.", ephemeral=True
        )
        return

    await interaction.response.send_modal(ClearSupplyModal())


class SupplyAuditView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

    container = discord.ui.Container()
    container.add_item(discord.ui.TextDisplay(texts.supply_audit_title))

    container.add_item(
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)
    )

    give_button = discord.ui.Button(
        label="Выдача склада",
        emoji="📝",
        style=discord.ButtonStyle.gray,
        custom_id="supply_audit_give",
    )
    give_button.callback = give_button_callback

    clear_button = discord.ui.Button(
        label="Очистка склада",
        emoji="🧹",
        style=discord.ButtonStyle.gray,
        custom_id="supply_audit_clear",
    )
    clear_button.callback = clear_button_callback

    action_row = discord.ui.ActionRow()
    action_row.add_item(give_button)
    action_row.add_item(clear_button)
    container.add_item(action_row)
