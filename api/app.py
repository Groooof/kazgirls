import inspect
import tracemalloc
from contextlib import asynccontextmanager
from datetime import UTC
from typing import Any

import fakeredis.aioredis
import socketio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI as _FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from pydantic import ValidationError
from redis.asyncio import ConnectionPool
from scalar_fastapi import get_scalar_api_reference
from sqladmin import Admin, BaseView
from sqladmin.authentication import AuthenticationBackend
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from admin.bases import CustomAdmin, authentication_backend
from app_logging import init_sentry, set_logging_config
from dependencies.db import EngineTypeEnum, _get_db, engines
from endpoints import external_api_router, internal_api_router
from exceptions.bases import LogicException
from settings.conf import databases, settings
from sockets import *  # noqa: F403
from sockets import register_handlers
from utils.handlers import any_exception_handler, logic_exception_handler, unhandled_validation_exception_handler
from utils.middleware import TracemallocMiddleware

origins = []


class FastAPI(_FastAPI):
    def simplify_operation_id(self) -> None:
        # from fastapi-utils/fastapi_utils/openapi.py
        for route in self.routes:
            if isinstance(route, APIRoute):
                route.operation_id = route.name

    def openapi(self) -> dict[str, Any]:
        self.simplify_operation_id()

        super().openapi()
        return self.openapi_schema  # type: ignore[return-value]


# Инициализируем админку
def register_admin_models(admin_app: Admin, db):
    import admin

    for _, class__ in inspect.getmembers(admin, inspect.isclass):
        is_bases = class__ == admin.BaseModelView or class__ == BaseView or class__ == admin.CustomBaseView
        if not is_bases and issubclass(class__, BaseView):
            if getattr(class__, "is_custom", False):  # в кастомные страницы прокинем зависимости для бд и редиса
                class__.db = db
                # так же в них authentication_backend, и чтоб декоратор login_required работал, нужно добавить
                class__.authentication_backend = admin_app.authentication_backend  #
            admin_app.add_view(class__)


def init_admin(
    app,
    engine,
    authentication_backend: AuthenticationBackend,
    db=None,
    middlewares: list[tuple] | None = None,
) -> None:
    middlewares = middlewares or []
    if settings.use_tracemalloc:
        middlewares.append((TracemallocMiddleware, (), {}))

    admin_app = CustomAdmin(
        app,
        engine,
        authentication_backend=authentication_backend,
        middlewares=middlewares,
        title="Project",
        templates_dir=str(settings.project_root / "templates"),
    )
    register_admin_models(admin_app, db)


def init_templates() -> Jinja2Templates:
    templates = Jinja2Templates(directory=settings.project_root / "templates")
    return templates


def init_scheduler():
    scheduler = AsyncIOScheduler(timezone=UTC)
    return scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    if databases.fake_redis:
        fake_redis = fakeredis.aioredis.FakeRedis()
        arq_pool = ArqRedis(fake_redis.connection_pool)
        redis_pool = fakeredis.aioredis.FakeRedis().connection_pool
    else:
        arq_pool_settings = RedisSettings.from_dsn(databases.arq_redis_url.unicode_string())
        arq_pool_settings.conn_retry_delay = 2
        arq_pool: ArqRedis = await create_pool(arq_pool_settings)
        redis_pool: ConnectionPool = ConnectionPool.from_url(databases.redis_url.unicode_string())

    scheduler = init_scheduler()
    scheduler.start()

    app.state.arq_pool = arq_pool
    app.state.redis_pool = redis_pool
    app.state.templates = init_templates()
    app.state.scheduler = scheduler

    yield

    scheduler.shutdown()
    await arq_pool.close()
    await redis_pool.disconnect()


def init_app():
    app = FastAPI(
        title="Project",
        version="1.0.0",
        debug=settings.debug,
        openapi_url="/openapi.json",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    app.mount("/static", StaticFiles(directory=settings.project_root / "statics", check_dir=False), name="static")

    allow_origins = origins if settings.is_prod else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.use_tracemalloc:
        app.add_middleware(TracemallocMiddleware)

    # Переопределим ошибки, которые будем райзить прямо в фукнции
    app.add_exception_handler(LogicException, logic_exception_handler)

    # ValidationError, который может не отловиться FastAPI
    app.add_exception_handler(ValidationError, unhandled_validation_exception_handler)
    # Все остальные системные ошибки, для однобразия ответов
    app.add_exception_handler(RequestValidationError, unhandled_validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, any_exception_handler)

    app.include_router(external_api_router, prefix=settings.api_v1_str)
    app.include_router(internal_api_router, prefix=settings.api_internal_str)

    @app.get("/docs", include_in_schema=False)
    async def scalar_docs():
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=app.title,
            dark_mode=False,
            hide_client_button=True,
        )

    return app


def init_sio():
    return socketio.AsyncServer(
        async_mode="asgi",
        client_manager=socketio.AsyncRedisManager(str(databases.sockets_redis_url)),
        cors_allowed_origins="*",
        logger=False,
        engineio_logger=False,
        transports=["websocket"],
    )


def init_sockets_app(sio, fastapi_app):
    register_handlers(sio)
    return socketio.ASGIApp(sio, other_asgi_app=fastapi_app)


def get_app() -> FastAPI:
    set_logging_config()

    if settings.use_tracemalloc:
        tracemalloc.start()

    init_sentry()

    app = init_app()
    init_admin(
        app,
        engines[EngineTypeEnum.DEFAULT_ENGINE],
        db=_get_db,
        authentication_backend=authentication_backend,
    )
    sio = init_sio()
    sockets_app = init_sockets_app(sio, app)
    return sockets_app
