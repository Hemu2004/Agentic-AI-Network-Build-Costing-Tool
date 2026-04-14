"""MongoDB connection and initialization."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING
from config import get_settings


_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        settings = get_settings()
        client = AsyncIOMotorClient(settings.mongodb_uri)
        _db = client[settings.mongodb_db]
        await init_db()
    return _db


async def init_db():
    """Create indexes and ensure collections exist."""
    db = await get_db()
    await db.projects.create_index([("created_at", ASCENDING)])
    await db.projects.create_index([("user_id", ASCENDING)])
    await db.projects.create_index([("type", ASCENDING)])
    await db.users.create_index("email", unique=True)
