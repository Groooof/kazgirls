from loguru import logger
from sqlalchemy import text

from dependencies import _get_redis
from dependencies.db import _get_db


async def check_connection_example_job():
    logger.info("Starting Example Connection Check Job")

    try:
        async with _get_redis() as redis, _get_db(use_default=True) as db:
            pong = await redis.ping()
            logger.info("Redis ping: {}", pong)

            result = await db.execute(text("SELECT 1"))
            logger.info("DB check: {}", result.scalar())

    except Exception:
        logger.exception("Error during connection check job")
