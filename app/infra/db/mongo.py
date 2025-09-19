from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

_client: Optional[AsyncIOMotorClient] = None

async def init_client():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URI)
        await get_db().command("ping")

async def close_client():
    global _client
    if _client is not None:
        _client.close()
        _client = None

def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("Mongo client not initialized")
    return _client

def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.MONGO_DB]