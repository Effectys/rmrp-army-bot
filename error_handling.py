import logging
import os
import traceback

import discord
from discord import app_commands

from utils.exceptions import StaticInputRequired

_original_view_on_error = discord.ui.View.on_error


async def _custom_view_on_error(
    self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
):
    """Глобальный обработчик ошибок View - игнорирует StaticInputRequired."""
    if isinstance(error, StaticInputRequired):
        return
    await _original_view_on_error(self, interaction, error, item)


async def on_tree_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError | str
):
    if isinstance(error, StaticInputRequired):
        return

    traceback_info = traceback.format_exc()
    error_id = os.urandom(4).hex()

    try:
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Команда ещё недоступна! Попробуйте ещё раз через **{error.retry_after:.2f}** сек!",
                ephemeral=True,
            )
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("У вас нет прав", ephemeral=True)
        elif isinstance(error, app_commands.CommandInvokeError) or isinstance(
            error, str
        ):
            embed = discord.Embed(
                title=f"💀 Произошла ошибка [{error_id}]",
                description=str(
                    error.original
                    if isinstance(error, app_commands.CommandInvokeError)
                    else error
                ),
                color=discord.Color.dark_grey(),
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            logging.warning(f"[{error_id}] Error: {error}")
            await interaction.response.send_message(
                f"### Произошла ошибка [{error_id}]", ephemeral=True
            )
    except:
        logging.error(f"[{error_id}] Unhandled error:", traceback_info)
