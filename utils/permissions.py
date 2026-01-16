import discord

import config
from database.models import User


async def get_user_rank(user_id: int) -> int | None:
    """Получить ранг пользователя по его Discord ID"""
    user = await User.find_one(User.discord_id == user_id)
    return user.rank if user else None


async def check_rank(
    interaction: discord.Interaction, min_rank: int, error_message: str | None = None
) -> bool:
    """
    Проверяет, имеет ли пользователь минимальный требуемый ранг.

    Args:
        interaction: Discord Interaction
        min_rank: Минимальный индекс ранга (используйте config.RankIndex)
        error_message: Сообщение об ошибке (по умолчанию генерируется автоматически)

    Returns:
        True если пользователь имеет достаточный ранг, False иначе
    """
    user = await User.find_one(User.discord_id == interaction.user.id)

    if not user or (user.rank or 0) < min_rank:
        if error_message is None:
            rank_name = (
                config.RANKS[min_rank]
                if min_rank < len(config.RANKS)
                else f"ранг {min_rank}"
            )
            error_message = f"❌ Доступно со звания {rank_name}."

        await interaction.response.send_message(error_message, ephemeral=True)
        return False

    return True


async def check_rank_silent(user_id: int, min_rank: int) -> bool:
    """
    Проверяет ранг без отправки сообщения об ошибке.

    Args:
        user_id: Discord ID пользователя
        min_rank: Минимальный индекс ранга

    Returns:
        True если пользователь имеет достаточный ранг
    """
    user = await User.find_one(User.discord_id == user_id)
    return user is not None and (user.rank or 0) >= min_rank


async def is_officer(user_id: int) -> bool:
    """Проверка на офицера (Капитан+)"""
    return await check_rank_silent(user_id, config.RankIndex.CAPTAIN)


async def is_senior_officer(user_id: int) -> bool:
    """Проверка на старшего офицера (Майор+)"""
    return await check_rank_silent(user_id, config.RankIndex.MAJOR)


async def is_high_command(user_id: int) -> bool:
    """Проверка на высшее командование (Полковник+)"""
    return await check_rank_silent(user_id, config.RankIndex.COLONEL)


async def is_general(user_id: int) -> bool:
    """Проверка на генерала (Генерал-майор+)"""
    return await check_rank_silent(user_id, config.RankIndex.MAJOR_GENERAL)
