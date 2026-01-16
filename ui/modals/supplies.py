import discord.ui


class ItemAmountModal(discord.ui.Modal):
    def __init__(self, item_name: str, current_qty: int = 0):
        super().__init__(title=f"Количество: {item_name[:20]}")
        self.item_name = item_name
        self.amount = discord.ui.TextInput(
            label="Введите количество",
            placeholder=f"Текущее: {current_qty}",
            default=str(current_qty) if current_qty > 0 else "",
            min_length=1,
            max_length=5,
            required=True,
        )
        self.add_item(self.amount)
        self.result = None

    async def on_submit(self, interaction: discord.Interaction):
        if not self.amount.value.isdigit():
            await interaction.response.send_message("❌ Введите число.", ephemeral=True)
            return

        qty = int(self.amount.value)
        if qty < 0:
            await interaction.response.send_message(
                "❌ Число не может быть отрицательным.", ephemeral=True
            )
            return

        self.result = qty
        await interaction.response.defer()
