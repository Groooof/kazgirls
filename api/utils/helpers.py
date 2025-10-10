import functools
import hashlib
import random
import re
import string
from collections.abc import Awaitable, Callable, Iterable, Mapping
from datetime import datetime

from pydantic import PostgresDsn
from sqlalchemy.ext.asyncio.session import AsyncSession, async_sessionmaker
from sqlalchemy.orm import (
    make_transient,
)
from sqlalchemy.orm.base import instance_state

from models.bases import BaseSQLAlchemyModel
from repository.bases import BaseSQLRepository
from settings.conf import ServerRole, settings


def convert_database_url(base_url: PostgresDsn, *, is_async: bool = True) -> str:
    params = base_url.hosts()[0]
    host = f"{params['host']}:{params['port']}" if params.get("port") else params["host"]
    new_url = f"postgresql+asyncpg://{params['username']}:{params['password']}@{host}{base_url.path}"
    if not is_async:
        new_url = new_url.replace("+asyncpg", "")
    return new_url


def generate_slug(phone_number: str) -> str:
    # Normalize phone number by removing non-digits
    clean_phone = re.sub(r"\D", "", phone_number)

    # Get current datetime with microseconds
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S%f")

    # Generate random bytes
    random_bytes = "".join(random.choices(string.ascii_letters + string.digits, k=16))  # noqa: S311

    # Combine all sources of entropy
    combined = f"{clean_phone}_{timestamp}_{random_bytes}"

    # Hash the combined string using SHA-256
    hashed = hashlib.sha256(combined.encode()).hexdigest()
    # Take first 12 characters of the hash for the slug
    slug = hashed[:12]

    return slug


def _find_db(obj):
    """Рекурсивный поиск `db` в сервисе или репозитории."""
    if isinstance(obj, AsyncSession):
        return obj
    if isinstance(obj, BaseSQLRepository):
        return obj.db
    if hasattr(obj, "__dict__"):
        for attr in vars(obj).values():
            found_db = _find_db(attr)
            if found_db:
                return found_db
    return None


def ensure_critical_transaction(func):
    """
    Декоратор для выполнения критически важных транзакций в отдельной сессии внутри сервисов и функций логики.
    Комитит изменения несмотря на райз ошибок

    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        is_method = bool(args) and isinstance(args[0], object) and not isinstance(args[0], AsyncSession)

        db = next((arg for arg in args if isinstance(arg, AsyncSession)), None) or next(
            (kwarg for kwarg in kwargs.values() if isinstance(kwarg, AsyncSession)), None
        )
        if not db and is_method:
            self = args[0]
            db = _find_db(self)

        if not db:
            return await func(*args, **kwargs)

        binds = getattr(db, "binds", {})

        async_session = async_sessionmaker(bind=db.bind, binds=binds, expire_on_commit=False, autoflush=False)

        async with async_session() as critical_session:
            kwargs = {
                key: (critical_session if isinstance(value, AsyncSession) else value) for key, value in kwargs.items()
            }
            if is_method:
                self = args[0]
                original_repos = {
                    name: repo for name, repo in self.__dict__.items() if isinstance(repo, BaseSQLRepository)
                }

                for name, repo in original_repos.items():
                    setattr(self, name, type(repo)(db=critical_session))  # Подмена репозиториев

                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception:
                    raise
                finally:
                    await critical_session.commit()
                    for name, repo in original_repos.items():
                        setattr(self, name, repo)  # Восстановление репозиториев
            else:
                new_args = tuple(critical_session if isinstance(arg, AsyncSession) else arg for arg in args)

                try:
                    result = await func(*new_args, **kwargs)
                    return result
                except Exception:
                    raise
                finally:
                    await critical_session.commit()

    return wrapper


def transient_models[RetT, **ParamsT](func: Callable[ParamsT, Awaitable[RetT]]) -> Callable[ParamsT, Awaitable[RetT]]:  # noqa: C901
    """
    Ставится поверх кэшируемой функции, чтобы отключить модели от сессии
    !!! Незагруженные relationships становятся None или пустым списком !!!
    """

    def _disconnect_model(model: RetT) -> None:
        if not isinstance(model, BaseSQLAlchemyModel):
            return

        for relationship in model.__mapper__.relationships:
            state = instance_state(model)
            relationship_value = state.dict.get(relationship.key)
            if relationship_value is None:
                continue
            if relationship.uselist:
                for related_obj in relationship_value:
                    _disconnect_model(related_obj)
            else:
                _disconnect_model(relationship_value)
        make_transient(model)

    def _disconnect_result(result: RetT) -> None:
        _disconnect_model(result)
        if isinstance(result, Mapping):
            for model in result.values():
                _disconnect_result(model)
        elif isinstance(result, Iterable):
            for model in result:
                _disconnect_result(model)

    @functools.wraps(func)
    async def wrapper(*args: ParamsT.args, **kwargs: ParamsT.kwargs) -> RetT:
        result = await func(*args, **kwargs)
        _disconnect_result(result)
        return result

    if settings.server_role == ServerRole.local:
        return func
    return wrapper
