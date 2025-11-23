from collections.abc import Callable
from contextlib import AsyncExitStack
from typing import NotRequired, TypedDict

import socketio
from aiobotocore.session import AioSession
from arq import ArqRedis
from clickhouse_connect.driver.asyncclient import AsyncClient as AsyncClickClient
from httpx import AsyncClient
from redis.asyncio import ConnectionPool, Redis
from sqlalchemy.ext.asyncio.session import AsyncSession
from types_aiobotocore_s3.client import S3Client


class JobContext(TypedDict):
    # системные поля
    _exit_stack: AsyncExitStack
    redis: ArqRedis  # задается в arq
    _redis_pool: ConnectionPool
    _db_maker: Callable[[], AsyncSession]

    # инициализируется в job_startup
    db_session: NotRequired[AsyncSession]
    redis_session: NotRequired[Redis]
    s3_session: NotRequired[AioSession]
    s3_client: NotRequired[S3Client]
    httpx_client: NotRequired[AsyncClient]
    click_client: NotRequired[AsyncClickClient]
    sio: NotRequired[socketio.AsyncServer]
