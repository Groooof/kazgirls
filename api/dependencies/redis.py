from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any

from fastapi import Request
from redis.asyncio import Redis

from settings.conf import databases


async def get_redis(request: Request) -> AsyncGenerator[Redis]:
    async with Redis(connection_pool=request.app.state.redis_pool) as redis:
        yield redis


@asynccontextmanager
async def _get_redis(*args) -> AsyncGenerator[Redis]:
    """Нужен для работы админки. Т.к starlette не работает с depends"""
    redis = Redis.from_url(databases.redis_url.unicode_string(), decode_responses=True)
    try:
        yield redis
    finally:
        await redis.close()


def with_redis():
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with _get_redis() as redis:
                if "redis" not in kwargs:
                    kwargs["redis"] = redis
                return await func(*args, **kwargs)

        return wrapper

    return decorator
