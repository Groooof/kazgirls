import string
from contextlib import asynccontextmanager
from random import sample

import fakeredis
import pytest_asyncio
import socketio
from alembic import command
from alembic.config import Config
from anyio import to_thread
from arq import ArqRedis
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from starlette.templating import Jinja2Templates

from admin.bases import AdminBackend
from app import FastAPI, init_admin, init_app, init_sockets_app
from app_logging import set_logging_config
from dependencies.db import get_db
from dependencies.httpx import get_httpx_client
from dependencies.redis import get_redis
from dependencies.tasks import get_task_manager
from dependencies.templates import get_templates
from models.bases import BaseSQLAlchemyModel
from settings.conf import databases, other_settings, settings
from tests.fake_repositories import FakeHttpxClient
from tests.fixtures.bases import load_fixtures


async def _create_database() -> str:
    engine = create_async_engine(databases.database_test_url, echo=False)
    db_name = "".join(sample(string.ascii_lowercase, 10))
    async with engine.begin() as conn:
        await conn.execute(text("COMMIT"))
        await conn.execute(text(f"CREATE DATABASE {db_name}"))
    await engine.dispose()
    return db_name


async def _drop_database(db_name):
    engine = create_async_engine(databases.database_test_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("COMMIT"))
        await conn.execute(text(f"DROP DATABASE {db_name}"))
    await engine.dispose()


async def _truncate(engine: AsyncEngine):
    # delete all table data (but keep tables)
    # we do cleanup before test 'cause if previous test errored,
    # DB can contain dust
    async with engine.begin() as conn:
        for table in BaseSQLAlchemyModel.metadata.sorted_tables:
            await conn.execute(text(f'ALTER TABLE "{table.name}" DISABLE TRIGGER ALL;'))
            await conn.execute(table.delete())
            await conn.execute(text(f'ALTER TABLE "{table.name}" ENABLE TRIGGER ALL;'))

        # only pg
        # tables = ','.join(t.fullname for t in BaseSQLAlchemyModel.metadata.sorted_tables)
        # await conn.execute(text(f'TRUNCATE {tables} RESTART IDENTITY'))


def _alembic_migrations(db_url: str):
    file_path = settings.project_root / "alembic.ini"
    alembic_cfg = Config(file_path)
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")


def _alembic_downgrade(db_url: str):
    alembic_cfg = Config(settings.project_root / "alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.downgrade(alembic_cfg, "base")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_dsn() -> str:
    db_dsn = databases.database_test_url
    if not databases.is_sqlite:
        db_name = await _create_database()
        db_dsn = f"{db_dsn.rsplit('/', 1)[0]}/{db_name}"

    await to_thread.run_sync(_alembic_migrations, db_dsn)

    yield db_dsn

    await to_thread.run_sync(_alembic_downgrade, db_dsn)

    if not databases.is_sqlite:
        await _drop_database(db_name)


@pytest_asyncio.fixture
async def engine(db_dsn: str) -> AsyncEngine:
    engine = create_async_engine(db_dsn, echo=settings.echo_sql)
    yield engine
    await _truncate(engine)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(engine: AsyncEngine) -> AsyncSession:
    async_session = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=True,
    )

    async with async_session() as session:
        if databases.is_sqlite:
            await session.execute(text("PRAGMA foreign_keys = 1"))

        await load_fixtures(session)
        yield session

        if databases.is_sqlite:
            await session.execute(text("PRAGMA foreign_keys = 0"))


@pytest_asyncio.fixture
async def redis() -> Redis:
    server = fakeredis.FakeServer()
    r = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield r


@pytest_asyncio.fixture
async def arq_redis():
    fake_redis = fakeredis.aioredis.FakeRedis()
    fake_arq_redis = ArqRedis(fake_redis.connection_pool)
    return fake_arq_redis


@pytest_asyncio.fixture
async def sio() -> socketio.AsyncServer:
    server = socketio.AsyncServer(
        async_mode="asgi",
        client_manager=socketio.AsyncRedisManager(str(databases.sockets_redis_url)),
        cors_allowed_origins="*",
        logger=False,
        engineio_logger=False,
        transports=["websocket"],
    )
    yield server


@pytest_asyncio.fixture
async def app(
    engine: AsyncEngine, db: AsyncSession, redis: Redis, arq_redis: ArqRedis, sio: socketio.AsyncServer
) -> FastAPI:
    """
    Создаем базу перед каждым тестом
    Если вынести инициализацию бд в override_get_db, то любой запрос к app будет с чистой базой,
    а нужно оставить scope на уровне функции
    """
    internal_app = init_app()

    set_logging_config()

    # настроим админку
    @asynccontextmanager
    async def override_get_db_context(*args) -> AsyncSession:
        yield db

    authentication_backend = AdminBackend(
        secret_key=settings.secret_key,
        engine=engine,
    )
    init_admin(
        internal_app,
        engine,
        db=override_get_db_context,
        authentication_backend=authentication_backend,
    )

    async def override_get_db() -> AsyncSession:
        return db

    async def override_get_redis():
        return redis

    async def override_get_task_manager():
        return arq_redis

    async def override_get_httpx_client():
        yield FakeHttpxClient()

    async def override_get_templates():
        yield Jinja2Templates(directory=settings.project_root / "templates")

    internal_app.dependency_overrides[get_db] = override_get_db
    internal_app.dependency_overrides[get_redis] = override_get_redis
    internal_app.dependency_overrides[get_task_manager] = override_get_task_manager
    internal_app.dependency_overrides[get_httpx_client] = override_get_httpx_client
    internal_app.dependency_overrides[get_templates] = override_get_templates
    sockets_app = init_sockets_app(sio, internal_app)
    yield sockets_app


@pytest_asyncio.fixture
async def client(app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"{other_settings.base_test_url.unicode_string()}{settings.api_v1_str[1:]}",
    ) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def auth_client(app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"{other_settings.base_test_url.unicode_string()}{settings.api_v1_str[1:]}",
    ) as test_client:
        response = (await test_client.post("/tokens/login", data={"username": "user", "password": "test"})).json()

        test_client.headers = {"Authorization": f"Bearer {response['access_token']}"}
        yield test_client
