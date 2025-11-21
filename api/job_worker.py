from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack
from functools import partial
from typing import Concatenate, cast

import socketio
from arq import cron
from arq.connections import RedisSettings
from arq.typing import WorkerCoroutine
from httpx import AsyncClient
from redis.asyncio import ConnectionPool, Redis
from sqlalchemy.ext.asyncio.session import AsyncSession

from app_logging import init_sentry, set_logging_config
from dependencies.db import get_binds
from schemas.jobs import JobContext
from settings.conf import databases, settings
from settings.db import EngineTypeEnum, engines
from tasks.streamers import clean_offline_streamers_task, clean_offline_viewers_task
from utils.constants import HOUR


async def startup(ctx: JobContext) -> None:  # pragma: no cover
    set_logging_config()
    init_sentry()

    # ctx содержит redis, но он именно ArqRedis. Сделаем стандартный
    redis_pool: ConnectionPool = ConnectionPool.from_url(databases.redis_url.unicode_string())
    ctx["_redis_pool"] = redis_pool
    ctx["_db_maker"] = partial(
        AsyncSession, bind=engines[EngineTypeEnum.DEFAULT_ENGINE], binds=get_binds(), expire_on_commit=True
    )


async def shutdown(ctx: JobContext) -> None:  # pragma: no cover
    await ctx["_redis_pool"].disconnect()


async def job_startup(ctx: JobContext) -> None:  # pragma: no cover
    exit_stack = AsyncExitStack()
    ctx["_exit_stack"] = exit_stack

    ctx["db_session"] = ctx["_db_maker"]()
    ctx["redis_session"] = Redis(connection_pool=ctx["_redis_pool"])
    ctx["httpx_client"] = AsyncClient()
    ctx["sio"] = socketio.AsyncServer(
        async_mode="asgi",
        client_manager=socketio.AsyncRedisManager(str(databases.sockets_redis_url), write_only=True),
        cors_allowed_origins="*",
        logger=False,
        engineio_logger=False,
        transports=["websocket"],
    )


async def job_shutdown(ctx: JobContext) -> None:  # pragma: no cover
    exit_stack: AsyncExitStack = ctx["_exit_stack"]
    redis_session = ctx["redis_session"]
    db_session = ctx["db_session"]
    httpx_client = ctx["httpx_client"]

    await exit_stack.aclose()

    await httpx_client.aclose()
    await db_session.commit()
    await db_session.close()
    await redis_session.close()


def repeat_every(interval: int, start: int = 0, end: int = 60) -> set[int]:
    return set(range(start, end, interval))


def adapt[**P, R](f: Callable[Concatenate[JobContext, P], Awaitable[R]]) -> WorkerCoroutine:
    return cast(WorkerCoroutine, f)


# ! DANGER: после таймаута arq скипнет таску и не заретраит.
# Использовать timeout_task. Ждать когда пофиксят обработку с TimeoutError
QUEUES = {
    "default": {
        "functions": [],
        "cron_jobs": [
            cron(adapt(clean_offline_streamers_task), max_tries=1, second=repeat_every(5)),
            cron(adapt(clean_offline_viewers_task), max_tries=1, second=repeat_every(5)),
        ],
    },
}
all_functions = [func for f in QUEUES.values() for func in f["functions"]]
all_cron_jobs = [func for f in QUEUES.values() for func in f["cron_jobs"]]
QUEUES["all"] = {"functions": all_functions, "cron_jobs": all_cron_jobs}


class Worker:  # pragma: no cover
    on_startup = startup
    on_shutdown = shutdown
    on_job_start = job_startup
    after_job_end = job_shutdown
    redis_settings = RedisSettings.from_dsn(databases.arq_redis_url.unicode_string())
    allow_abort_jobs = True
    max_tries = 5
    keep_result = 0  # не храним результаты в общем случае
    job_timeout = 2 * HOUR  # ставим больше, чем есть в вызовах timeout_task()

    functions = QUEUES[settings.arq_queue]["functions"]
    cron_jobs = QUEUES[settings.arq_queue]["cron_jobs"]
