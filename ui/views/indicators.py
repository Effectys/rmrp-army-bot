import discord.ui


def indicator_view(text: str, emoji: str | None = None):
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label=text, emoji=emoji, disabled=True))
    return view
