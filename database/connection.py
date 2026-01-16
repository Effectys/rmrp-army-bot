import logging

from beanie import init_beanie
from pymongo import AsyncMongoClient

import config
from database.counters import Counter
from database.models import (
    BottomMessage,
    DismissalRequest,
    Division,
    ReinstatementRequest,
    RoleRequest,
    SupplyRequest,
    TransferRequest,
    User,
)

_IS_INITIALIZED = False
MODELS = [
    User,
    Division,
    ReinstatementRequest,
    BottomMessage,
    RoleRequest,
    SupplyRequest,
    DismissalRequest,
    TransferRequest,
    Counter,
]


async def establish_db_connection():
    global _IS_INITIALIZED
    if _IS_INITIALIZED:
        return

    client = AsyncMongoClient(config.MONGO_URI)

    await init_beanie(
        database=client.get_database(config.MONGO_DB_NAME), document_models=MODELS
    )

    _IS_INITIALIZED = True
    logging.info("Database connection established")
