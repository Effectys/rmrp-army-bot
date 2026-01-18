import discord

import config
from database.models import User
from utils.user_data import format_game_id, formatted_static_to_int


class StaticInputModal(discord.ui.Modal, title="Введите ваш статик"):
    static_input = discord.ui.TextInput(
        label="Статик",
        placeholder="XXX-XXX",
        max_length=7,
    )

    async def on_submit(self, interaction: discord.Interaction):
        static_str = self.static_input.value
        static_int = formatted_static_to_int(static_str)

        if static_int is None:
            await interaction.response.send_message(
                "❌ Некорректный формат статика.", ephemeral=True
            )
            return

        user = await User.find_one(User.discord_id == interaction.user.id)
        if not user:
            await interaction.response.send_message(
                "❌ Пользователь не найден в базе данных.", ephemeral=True
            )
            return

        user.static = static_int
        await user.save()

        channel = interaction.client.get_channel(config.CHANNELS["static_log"])
        if channel:
            embed = discord.Embed(
                title="Самостоятельный ввод статика",
                color=discord.Color.orange(),
            )
            embed.add_field(
                name="Пользователь",
                value=f"{interaction.user.mention} ({interaction.user.display_name})",
                inline=False,
            )
            embed.add_field(
                name="Имя в системе",
                value=user.full_name or "Не указано",
                inline=False,
            )
            embed.add_field(
                name="Звание",
                value=config.RANKS[user.rank] if user.rank is not None else "Нет",
                inline=False,
            )
            embed.add_field(
                name="Введенный статик",
                value=f"`{format_game_id(static_int)}`",
                inline=False,
            )
            embed.set_footer(text="Проверьте корректность данных")

            await channel.send(
                content="-# Требуется проверка. "
                "При несовпадении — измените через команду редактирования.",
                embed=embed,
            )

        await interaction.response.send_message(
            "✅ Статик сохранен. Теперь вы можете повторить действие.",
            ephemeral=True,
        )
