from typing import TYPE_CHECKING, Any

from app.config import Settings

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


def create_mongo_client(settings: Settings) -> Any:
    # 延迟导入,避免测试环境强依赖 motor
    from motor.motor_asyncio import AsyncIOMotorClient

    return AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)


def get_mongo_db(client: Any, settings: Settings) -> Any:
    return client[settings.MONGODB_DB]
