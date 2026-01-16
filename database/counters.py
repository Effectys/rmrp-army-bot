from beanie import Document
from pymongo import ReturnDocument


class Counter(Document):
    """Счетчик для атомарной генерации ID"""

    name: str
    value: int = 0

    class Settings:
        name = "counters"


async def get_next_id(collection_name: str) -> int:
    """
    Атомарно получает следующий ID для указанной коллекции.
    Использует findAndModify с upsert и $inc для предотвращения race conditions.
    """
    result = await Counter.get_pymongo_collection().find_one_and_update(
        {"name": collection_name},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    return result["value"]
