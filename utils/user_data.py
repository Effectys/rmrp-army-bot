import discord

statics_cache = {}
names_cache = {}


async def ask_game_id(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("")


async def get_full_name(interaction: discord.Interaction) -> str | None:
    if interaction.user.id in names_cache:
        return names_cache[interaction.user.id]

    from database.models import User

    user_info = await User.find_one(User.discord_id == interaction.user.id)
    if user_info and user_info.first_name and user_info.last_name:
        full_name = f"{user_info.first_name} {user_info.last_name}"
        names_cache[interaction.user.id] = full_name
        return full_name
    else:
        return None


def format_game_id(game_id: int) -> str:
    game_id_str = str(game_id).zfill(6)
    return f"{game_id_str[:3]}-{game_id_str[3:]}"


def formatted_static_to_int(static_str: str) -> int | None:
    cleaned = "".join(filter(str.isdigit, static_str)).lstrip("0")
    if cleaned == "":
        return 0
    try:
        return int(cleaned)
    except ValueError:
        return None


def transliterate_abbreviation(abbreviation: str) -> str:
    translit_map = {
        "А": "A",
        "В": "B",
        "Е": "E",
        "К": "K",
        "М": "M",
        "Н": "H",
        "О": "O",
        "Р": "P",
        "С": "C",
        "Т": "T",
        "Х": "X",
    }
    return "".join(translit_map.get(char, char) for char in abbreviation)


def parse_full_name(full_name: str) -> tuple[str, str] | None:
    """
    Парсит полное имя в формате "Имя Фамилия".
    Возвращает (first_name, last_name) или None если формат неверный.
    """
    parts = full_name.strip().split(" ", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


async def update_user_name_if_changed(
    user, full_name: str, initiator: discord.Member | None = None
) -> bool:
    """
    Обновляет имя пользователя если оно отличается от текущего.
    Если передан initiator, логирует изменение в кадровый аудит.
    Возвращает True если имя было обновлено.
    """
    parsed = parse_full_name(full_name)
    if not parsed:
        return False

    first_name, last_name = parsed
    if user.first_name != first_name or user.last_name != last_name:
        user.first_name = first_name
        user.last_name = last_name
        await user.save()

        if initiator:
            from utils.audit import AuditAction, audit_logger

            await audit_logger.log_action(
                action=AuditAction.NICKNAME_CHANGED,
                initiator=initiator,
                target=user.discord_id,
            )

        return True
    return False
