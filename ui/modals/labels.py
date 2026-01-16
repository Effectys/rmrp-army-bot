import discord.ui


def name_component():
    return discord.ui.TextInput(
        label="Ваше имя и фамилия", placeholder="Артём Царёв", max_length=25
    )


def static_label():
    return discord.ui.Label(
        text="Ваш «Статик»",
        description="Статик - ваш игровой идентификатор. Посмотреть его можно в вашем паспорте, он будет формата XXX-XXX.",
        component=discord.ui.TextInput(
            style=discord.TextStyle.short, placeholder="XXX-XXX", max_length=7
        ),
    )


def static_reminder():
    return discord.ui.TextDisplay("Ваш статик уже установлен в системе.")


def screenshot_label(element: str):
    return discord.ui.Label(
        text=f"Копия {element}",
        description=f"Загрузите на фотохостинг скриншот {element} и вставьте ссылку.",
        component=discord.ui.TextInput(
            style=discord.TextStyle.short,
            placeholder=f"Ссылка на скриншот {element}",
            max_length=200,
        ),
    )
