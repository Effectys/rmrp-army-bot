import logging
from typing import Optional

import discord

from utils.audit import AuditAction, action_emojis

logger = logging.getLogger(__name__)


async def _send_dm(bot, user_id: int, embed: discord.Embed) -> bool:
    try:
        user = await bot.fetch_user(user_id)
        await user.send(embed=embed)
        return True
    except discord.Forbidden:
        logger.debug(f"Cannot send DM to user {user_id}: DMs are closed")
        return False
    except discord.NotFound:
        logger.debug(f"Cannot send DM to user {user_id}: user not found")
        return False
    except discord.HTTPException as e:
        logger.warning(f"Failed to send DM to user {user_id}: {e}")
        return False


async def notify_role_approved(bot, user_id: int, role_type: str) -> bool:
    """Уведомление об одобрении заявки на роль."""
    embed = discord.Embed(
        title=f"{action_emojis[AuditAction.INVITED]} Заявка одобрена",
        description=f"Ваша заявка на роль **{role_type}** была одобрена.",
        color=discord.Color.green(),
    )
    embed.set_footer(text="Добро пожаловать!")
    return await _send_dm(bot, user_id, embed)


async def notify_reinstatement_approved(bot, user_id: int, rank: str) -> bool:
    """Уведомление об одобрении восстановления."""
    embed = discord.Embed(
        title=f"{action_emojis[AuditAction.REINSTATEMENT]} Восстановление одобрено",
        description=f"Ваше заявление на восстановление было одобрено.\n"
        f"Вам присвоено звание: **{rank}**.",
        color=discord.Color.green(),
    )
    embed.set_footer(text="С возвращением!")
    return await _send_dm(bot, user_id, embed)


async def notify_transfer_approved(bot, user_id: int, new_division: str) -> bool:
    """Уведомление об одобрении перевода."""
    embed = discord.Embed(
        title=f"{action_emojis[AuditAction.DIVISION_CHANGED]} "
        f"Перевод в подразделение одобрен",
        description=f"Ваше заявление на перевод было одобрено.\n"
        f"Вы переведены в подразделение: **{new_division}**.",
        color=discord.Color.blue(),
    )
    return await _send_dm(bot, user_id, embed)


async def notify_promoted(bot, user_id: int, new_rank: str) -> bool:
    """Уведомление о повышении звания."""
    embed = discord.Embed(
        title=f"{action_emojis[AuditAction.PROMOTED]} Повышение звания",
        description=f"Поздравляем! Вам присвоено новое звание: **{new_rank}**.",
        color=discord.Color.green(),
    )
    return await _send_dm(bot, user_id, embed)


async def notify_unblacklisted(bot, user_id: int) -> bool:
    """Уведомление о снятии с черного списка."""
    embed = discord.Embed(
        title="Снятие с черного списка",
        description="Вы были сняты с черного списка.",
        color=discord.Color.green(),
    )
    return await _send_dm(bot, user_id, embed)


async def notify_role_rejected(
    bot, user_id: int, role_type: str, reason: Optional[str] = None
) -> bool:
    """Уведомление об отклонении заявки на роль."""
    description = f"Ваша заявка на роль **{role_type}** была отклонена."
    if reason:
        description += f"\n\n**Причина:** {reason}"

    embed = discord.Embed(
        title=f"{action_emojis[AuditAction.DISMISSED]} Заявка отклонена",
        description=description,
        color=discord.Color.red(),
    )
    return await _send_dm(bot, user_id, embed)


async def notify_dismissed(
    bot, user_id: int, reason: str, by_report: bool = False
) -> bool:
    """Уведомление об увольнении."""
    title = "Увольнение по рапорту" if by_report else "Увольнение"

    embed = discord.Embed(
        title=title,
        description=f"{action_emojis[AuditAction.DISMISSED]} Вы были уволены."
        f"\n\n**Причина:** {reason}",
        color=discord.Color.red(),
    )
    return await _send_dm(bot, user_id, embed)


async def notify_blacklisted(bot, user_id: int, reason: str, duration: str) -> bool:
    """Уведомление о добавлении в черный список."""
    embed = discord.Embed(
        title="⬛ Добавление в черный список",
        description=f"Вы были добавлены в черный список.\n\n"
        f"**Причина:** {reason}\n**Срок:** {duration}",
        color=discord.Color.red(),
    )
    return await _send_dm(bot, user_id, embed)


async def notify_reinstatement_rejected(
    bot, user_id: int, reason: Optional[str] = None
) -> bool:
    """Уведомление об отклонении восстановления."""
    description = "Ваше заявление на восстановление было отклонено."
    if reason:
        description += f"\n\n**Причина:** {reason}"

    embed = discord.Embed(
        title=f"{action_emojis[AuditAction.REINSTATEMENT]} Восстановление отклонено",
        description=description,
        color=discord.Color.red(),
    )
    return await _send_dm(bot, user_id, embed)


async def notify_transfer_rejected(bot, user_id: int, reason: str) -> bool:
    """Уведомление об отклонении перевода."""
    embed = discord.Embed(
        title=f"{action_emojis[AuditAction.DIVISION_CHANGED]} Перевод отклонен",
        description=f"Ваше заявление на перевод было отклонено.\n\n"
        f"**Причина:** {reason}",
        color=discord.Color.red(),
    )
    return await _send_dm(bot, user_id, embed)


async def notify_demoted(bot, user_id: int, new_rank: str) -> bool:
    """Уведомление о понижении звания."""
    embed = discord.Embed(
        title=f"{action_emojis[AuditAction.DEMOTED]} Понижение звания",
        description=f"Вам было понижено звание до: **{new_rank}**.",
        color=discord.Color.red(),
    )
    return await _send_dm(bot, user_id, embed)


async def notify_position_changed(bot, user_id: int, new_position: str) -> bool:
    """Уведомление об изменении должности."""
    embed = discord.Embed(
        title=f"{action_emojis[AuditAction.POSITION_CHANGED]} Изменение должности",
        description=f"Ваша должность была изменена на: **{new_position}**.",
        color=discord.Color.blue(),
    )
    return await _send_dm(bot, user_id, embed)

async def notify_timeoff_approved(bot, user_id: int) -> bool:
    """Уведомление об одобрении заявки на отгул."""
    embed = discord.Embed(
        title=f"{action_emojis[AuditAction.INVITED]} Заявка одобрена",
        description=f"Ваша заявка на отгул была одобрена.",
        color=discord.Color.green(),
    )
    return await _send_dm(bot, user_id, embed)

async def notify_timeoff_rejected(
    bot, user_id: int, reason: Optional[str] = None
) -> bool:
    """Уведомление об отклонении заявки на отгул."""
    description = f"Ваша заявка на отгул была отклонена."
    if reason:
        description += f"\n\n**Причина:** {reason}"

    embed = discord.Embed(
        title=f"{action_emojis[AuditAction.DISMISSED]} Заявка отклонена",
        description=description,
        color=discord.Color.red(),
    )
    return await _send_dm(bot, user_id, embed)