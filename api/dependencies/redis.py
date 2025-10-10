from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Request
from redis.asyncio import Redis

from settings.conf import databases


async def get_redis(request: Request) -> AsyncGenerator[Redis]:
    async with Redis(connection_pool=request.app.state.redis_pool) as redis:
        yield redis


@asynccontextmanager
async def _get_redis(*args) -> AsyncGenerator[Redis]:
    """Нужен для работы админки. Т.к starlette не работает с depends"""
    redis = Redis.from_url(databases.redis_url.unicode_string())
    try:
        yield redis
    finally:
        await redis.close()
