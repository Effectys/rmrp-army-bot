import discord.ui


def name_component():
    return discord.ui.TextInput(
        label="Ваше имя и фамилия", placeholder="Иван Иванов", max_length=25
    )


def static_label():
    description = (
        "Статик - ваш игровой идентификатор. "
        "Посмотреть его можно в вашем паспорте, он будет формата XXX-XXX."
    )
    return discord.ui.Label(
        text="Ваш «Статик»",
        description=description,
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

def period():
    return discord.ui.TextInput(
        label="Период", placeholder="17:00 - 18:00", max_length=25
    )
