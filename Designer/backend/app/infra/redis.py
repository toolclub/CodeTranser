from typing import Any

from app.config import Settings


def create_redis(settings: Settings) -> Any:
    # 延迟导入,测试环境允许缺 redis 包
    from redis.asyncio import from_url

    return from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        health_check_interval=30,
    )
