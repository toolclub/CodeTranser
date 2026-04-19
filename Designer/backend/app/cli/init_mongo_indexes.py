from typing import Any

from app.infra.mongo.collections import RUN_STEP_DETAILS, SANDBOX_TRACES

TTL_90_DAYS_SECONDS = 90 * 86400


async def ensure_indexes(db: Any) -> None:
    await db[RUN_STEP_DETAILS].create_index([("run_id", 1), ("step_id", 1)], unique=True)
    await db[RUN_STEP_DETAILS].create_index(
        [("created_at", 1)], expireAfterSeconds=TTL_90_DAYS_SECONDS
    )
    await db[SANDBOX_TRACES].create_index([("run_id", 1)])
    await db[SANDBOX_TRACES].create_index(
        [("created_at", 1)], expireAfterSeconds=TTL_90_DAYS_SECONDS
    )
