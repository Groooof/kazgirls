from datetime import timedelta
from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import (
    AnyHttpUrl,
    PostgresDsn,
    RedisDsn,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerRole(str, Enum):
    local = "local"
    dev = "dev"
    prod = "prod"


class CustomBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def is_pytest(self):
        import os

        return os.environ.get("PYTEST_CURRENT_TEST") is not None


class Settings(CustomBaseSettings):
    secret_key: str

    debug: bool = False
    server_role: ServerRole = ServerRole.local
    enable_request_log: bool = False

    root_path: str = "/api"
    project_root: Path = Path(__file__).resolve().parent.parent
    api_v1_str: str = "/api/v1"
    api_internal_str: str = "/api-internal/v1"

    sentry_url: str = ""
    log_level: str = "info" if server_role == ServerRole.prod else "debug"
    serialize_logs: bool = False
    local_log_path: str = ""
    use_tracemalloc: bool = False
    echo_sql: bool = False

    app_reload: bool = server_role != ServerRole.prod
    frontend_host: str = "https://link.kazgirls.com"

    @property
    def is_prod(self):
        return self.server_role == ServerRole.prod

    @property
    def is_local(self):
        return self.server_role == ServerRole.local


class SocketsNamespaces(CustomBaseSettings):
    streamers: str = "/streamers"
    lobby: str = "/lobby"


class OtherSettings(CustomBaseSettings):
    jwt_secret: str = "test"  # noqa: S105
    users_session_ttl: timedelta = timedelta(days=30)
    access_token_cookie_name: str = "access_token"  # noqa: S105
    default_timezone: str = "Europe/Moscow"
    default_dt_format: str = "%d/%m/%Y, %I:%M %p"

    base_test_url: AnyHttpUrl = "http://127.0.0.1:8000"


class Databases(CustomBaseSettings):
    database_url: PostgresDsn = "postgresql+asyncpg://test:test@localhost:5422/test"
    database_test_url: str = "postgresql+asyncpg://test:test@localhost:5422/testdb"  # "sqlite+aiosqlite:///:memory:"
    request_log_database_url: PostgresDsn = "postgresql+asyncpg://test:test@localhost/request_log"
    is_sqlite: bool = False

    arq_redis_url: RedisDsn = "redis://default:vuop7Aithohw@127.0.0.1:6666/1"
    sockets_redis_url: RedisDsn = "redis://default:vuop7Aithohw@127.0.0.1:6666/0"
    redis_url: RedisDsn = "redis://default:vuop7Aithohw@127.0.0.1:6666/0"
    fake_redis: bool = False

    def _get_db(self) -> PostgresDsn:
        val = self.database_url if not self.is_pytest else self.database_test_url
        return PostgresDsn(val)


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_sockets_namespaces() -> SocketsNamespaces:
    return SocketsNamespaces()


@lru_cache
def get_other() -> OtherSettings:
    return OtherSettings()


@lru_cache
def get_database_settings() -> Databases:
    return Databases()


settings: Settings = get_settings()
other_settings: OtherSettings = get_other()
sockets_namespaces: SocketsNamespaces = get_sockets_namespaces()
databases: Databases = get_database_settings()
