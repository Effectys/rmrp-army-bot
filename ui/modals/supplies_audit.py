import discord.ui
from discord import Interaction
from discord._types import ClientT


class GiveSupplyModal(discord.ui.Modal, title="Выдача снабжения"):
    to_whom = discord.ui.Label(
        text="Кому выдаете снабжение?",
        description="Выберите военнослужащего, которому вы хотите выдать снабжение.",
        component=discord.ui.UserSelect(
            placeholder="Выберите пользователя",
            min_values=1,
            max_values=1,
            required=True,
        ),
    )
    items = discord.ui.TextInput(
        label="Снабжение",
        placeholder="Перечислите, что вы выдаете",
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=1000,
        required=True,
    )
    reason = discord.ui.TextInput(
        label="Причина выдачи",
        placeholder="Укажите причину выдачи снабжения",
    )

    async def on_submit(self, interaction: Interaction[ClientT], /) -> None:
        selected_user = self.to_whom.component.values[0]
        items_list = self.items.value.splitlines()
        reason_text = self.reason.value if self.reason.value else "Не указана"

        confirmation_message = "✅ Снабжение выдается пользователю..."
        await interaction.response.send_message(confirmation_message, ephemeral=True)

        embed = discord.Embed(
            title="📦 Выдача снабжения",
            color=discord.Color.dark_green(),
            timestamp=interaction.created_at,
        )
        embed.add_field(name="Выдал", value=interaction.user.mention, inline=True)
        embed.add_field(name="Получил", value=selected_user.mention, inline=True)
        embed.add_field(
            name="Предметы",
            value="\n".join(f"- {item}" for item in items_list),
            inline=False,
        )
        embed.add_field(name="Причина", value=reason_text, inline=False)
        await interaction.channel.send(embed=embed)

        from cogs.supplies_audit import update_bottom_message

        await update_bottom_message(interaction.client)


class ClearSupplyModal(discord.ui.Modal, title="Выдача снабжения"):
    job = discord.ui.TextInput(
        label="Действие",
        placeholder="Перечислите выполненные на складе действия",
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=1000,
        required=True,
    )

    async def on_submit(self, interaction: Interaction[ClientT], /) -> None:
        job_list = self.job.value.splitlines()

        confirmation_message = "✅ Запись отправляется..."
        await interaction.response.send_message(confirmation_message, ephemeral=True)

        embed = discord.Embed(
            title="🧹 Чистка склада",
            color=discord.Color.gold(),
            timestamp=interaction.created_at,
        )
        embed.add_field(
            name="Ответственный", value=interaction.user.mention, inline=True
        )
        embed.add_field(
            name="Предметы",
            value="\n".join(f"- {item}" for item in job_list),
            inline=False,
        )
        await interaction.channel.send(embed=embed)

        from cogs.supplies_audit import update_bottom_message

        await update_bottom_message(interaction.client)
