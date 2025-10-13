import enum

import orjson
from pydantic import PostgresDsn
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from settings.conf import databases, settings
from utils.libs import orjson_serializer


class EngineTypeEnum(str, enum.Enum):
    DEFAULT_ENGINE = "default"
    DEFAULT_REPLICA_ENGINE = "default_replica"


def convert_posgres_url(base_url: PostgresDsn):
    url_data = base_url.hosts()[0]
    host = f"{url_data['host']}:{url_data['port']}" if url_data["port"] else url_data["host"]
    new_url = f"postgresql+asyncpg://{url_data['username']}:{url_data['password']}@{host}{base_url.path}"
    return new_url


ENGINE_CONFIG = {
    "echo": settings.echo_sql,
    "pool_size": 10,
    "json_serializer": orjson_serializer,
    "json_deserializer": orjson.loads,
    "pool_recycle": 1200,
}


engines: dict[str, AsyncEngine] = {
    EngineTypeEnum.DEFAULT_ENGINE: create_async_engine(convert_posgres_url(databases.database_url), **ENGINE_CONFIG),
}
