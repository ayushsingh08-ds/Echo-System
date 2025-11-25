from motor.motor_asyncio import AsyncIOMotorClient
from ..config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]

def get_collection():
    return db[settings.MONGO_COLL]
