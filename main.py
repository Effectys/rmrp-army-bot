import logging

import discord

import config
from bot import Bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


def main():
    token = config.TOKEN

    intents = discord.Intents.all()
    bot = Bot(command_prefix="!", intents=intents)

    bot.run(token)


if __name__ == "__main__":
    main()
