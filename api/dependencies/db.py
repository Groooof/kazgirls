import inspect
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from functools import lru_cache, wraps
from typing import Any

from sqlalchemy.ext.asyncio.session import AsyncSession, async_sessionmaker

import models
from settings.db import EngineTypeEnum, engines


@lru_cache
def get_binds():
    # для определения в какую бд слать запрос, в моделях прописываем __engine__
    binds = {}
    for _, class__ in inspect.getmembers(models, inspect.isclass):
        if getattr(class__, "__engine__", None):
            binds[class__] = engines.get(class__.__engine__) or engines[EngineTypeEnum.DEFAULT_ENGINE]
    return binds


SessionMaker = async_sessionmaker(bind=engines[EngineTypeEnum.DEFAULT_ENGINE], binds=get_binds())


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSession(bind=engines[EngineTypeEnum.DEFAULT_ENGINE], binds=get_binds()) as session:  # noqa: SIM117
        async with session.begin():
            yield session


@asynccontextmanager
async def _get_db(*args, use_default: bool = False) -> AsyncIterator[AsyncSession]:
    "Для админки. expire_on_commit=False - избавляет от проблемы sqlalchemy.orm.exc.DetachedInstanceError"

    bind = engines[EngineTypeEnum.DEFAULT_ENGINE] if use_default else None
    async with AsyncSession(bind=bind, binds=get_binds(), expire_on_commit=False) as session:  # noqa: SIM117
        async with session.begin():
            yield session


def with_db(use_default: bool = False):
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with _get_db(use_default=use_default) as db:
                return await func(*args, db=db, **kwargs)

        return wrapper

    return decorator
