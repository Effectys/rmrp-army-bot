import logging

import discord

from database.models import BottomMessage

logger = logging.getLogger(__name__)


async def update_bottom_message(
    bot, channel_id: int, view: discord.ui.View, embed: discord.Embed | None = None
) -> discord.Message | None:
    """
    Обновляет "закрепленное" сообщение внизу канала.
    Удаляет старое сообщение и создает новое с указанным view и embed.

    Args:
        bot: Экземпляр бота
        channel_id: ID канала
        view: View для сообщения
        embed: Опциональный Embed для сообщения

    Returns:
        Новое сообщение или None если канал не найден
    """
    bottom_message = await BottomMessage.find_one(
        BottomMessage.channel_id == channel_id
    )

    if bottom_message:
        try:
            await bot.http.delete_message(channel_id, bottom_message.message_id)
        except discord.NotFound:
            logger.debug(f"Bottom message {bottom_message.message_id} already deleted")
        except discord.Forbidden:
            logger.warning(f"No permission to delete message in channel {channel_id}")
        except Exception as e:
            logger.error(f"Failed to delete bottom message: {e}")

    channel = bot.get_channel(channel_id)
    if not channel:
        logger.warning(f"Channel {channel_id} not found")
        return None

    new_message = await channel.send(embed=embed, view=view)

    if bottom_message:
        bottom_message.message_id = new_message.id
        await bottom_message.save()
    else:
        new_bottom_message = BottomMessage(
            channel_id=channel_id, message_id=new_message.id
        )
        await new_bottom_message.create()

    return new_message
