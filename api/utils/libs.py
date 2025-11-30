import asyncio
import inspect
import signal
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie
from typing import Concatenate, Literal, Optional, overload
from urllib.parse import parse_qs

import orjson
import phonenumbers
from aiocache import cached as aiocache
from loguru import logger
from phonenumbers import (
    NumberParseException,
    PhoneNumberFormat,
    PhoneNumberType,
    format_number,
    is_valid_number,
    number_type,
    parse,
    parse as parse_phone_number,
)
from phonenumbers.phonenumber import PhoneNumber
from pydantic import BaseModel, create_model

from settings.conf import ServerRole, settings

MOBILE_NUMBER_TYPES = PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE


def utc_now():
    return datetime.now(tz=UTC)


def orjson_serializer(obj):
    # Note that `orjson.dumps()` return byte array, while sqlalchemy expects string, thus `decode()` call.
    return orjson.dumps(obj, option=orjson.OPT_NAIVE_UTC | orjson.OPT_NON_STR_KEYS).decode()


def get_country_code_for_phoneval(phoneval: str) -> str:
    phoneobj = phonenumbers.parse(phoneval)
    country_code = phonenumbers.region_code_for_number(phoneobj)
    if country_code is None:
        raise ValueError("Unavailable get country code")

    return country_code.upper()


def get_call_range_by_id(_id: int, search_call_period: timedelta = timedelta(days=1)) -> tuple[datetime, datetime]:
    try:
        min_date = datetime.strptime(str(_id)[:6], "%y%m%d").replace(tzinfo=UTC)
        max_date = min_date + search_call_period
    except ValueError:
        max_date = datetime.now(UTC)
        min_date = max_date - search_call_period

    return min_date, max_date


def format_as_e164(phone) -> str:
    return format_number(phone, PhoneNumberFormat.E164)


def format_as_8(phone) -> str:
    return format_as_e164(phone).replace("+7", "8")


def parse_number(v, region: str | None = None, mobile: bool = True):
    if v is None:
        return v

    try:
        n = parse_phone_number(v, region)
    except NumberParseException:
        raise ValueError("Please provide a valid phone number")

    if not is_valid_number(n) or mobile and number_type(n) not in MOBILE_NUMBER_TYPES:
        raise ValueError("Please provide a valid mobile phone number")

    return format_number(n, PhoneNumberFormat.E164)


def is_mobile(value: PhoneNumber | str) -> bool:
    return number_type(value if isinstance(value, PhoneNumber) else parse(value)) in MOBILE_NUMBER_TYPES


def force_str(s, encoding="utf-8", errors="strict") -> str:
    """
    May raise an exception UnicodeDecodeError
    """
    # Handle the common case first for performance reasons.
    if issubclass(type(s), str):
        return s

    args = (encoding, errors) if isinstance(s, bytes) else set()
    return str(s, *args)


def force_bytes(s, encoding="utf-8", errors="strict") -> bytes:
    """
    Similar to smart_bytes, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first for performance reasons.
    if isinstance(s, bytes):
        if encoding == "utf-8":
            return s
        else:
            return s.decode("utf-8", errors).encode(encoding, errors)
    if isinstance(s, memoryview):
        return bytes(s)
    return str(s).encode(encoding, errors)


@overload
def optional_model(cls: type[BaseModel]) -> type[BaseModel]: ...


@overload
def optional_model(cls: str, *not_optional_fields: tuple[str, ...]) -> Callable[[type[BaseModel]], type[BaseModel]]: ...


def optional_model(cls, *not_optional_fields):
    """
    Декоратор для pydantic моделей.
    **Не учитывает дефолтные значения опциональных полей, если не переданы явно, то объявляются None**

    Все поля опциональны
    @optional_model
    class Example(BaseModel):
        ...

    Конкретные поля неизменны (остальные опциональны)
    @optional_model('something')
    class Example(BaseModel):
        ...
    """

    def deco(_cls: type[BaseModel], /) -> type[BaseModel]:
        fields_dict = {}
        for field in _cls.model_fields:
            field_info = _cls.model_fields[field]
            if field in not_optional_fields:
                new_annotations = field_info.annotation
            else:
                field_info.default = None
                field_info.default_factory = None
                new_annotations = Optional[field_info.annotation]  # noqa: UP007,UP045
            fields_dict[field] = (new_annotations, field_info)

        _optional_model = create_model(_cls.__name__, **fields_dict)
        _optional_model.__module__ = _cls.__module__
        return _optional_model

    if inspect.isclass(cls) and issubclass(cls, BaseModel):
        return deco(cls)

    not_optional_fields = (cls,) + not_optional_fields
    return deco


async def cancel_task(task: asyncio.Task, raise_error: bool = True):
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:
        if raise_error:
            raise
        else:
            logger.exception("Cancelling task exception")
    # other errors will be raised


async def wait_exit_signal():
    exit_event = asyncio.Event()

    signal_func = asyncio.get_running_loop().add_signal_handler
    signal_func(signal.SIGTERM, exit_event.set)
    signal_func(signal.SIGHUP, exit_event.set)
    signal_func(signal.SIGINT, exit_event.set)

    await exit_event.wait()


async def delay(delay, coro):
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        await cancel_task(asyncio.create_task(coro))
        raise
    else:
        await coro


async def catch(coro):
    try:
        await coro
    except Exception:  # noqa
        logger.exception("Coro failed")


def cached(*args, **kwargs):
    def wrapped(func):
        if settings.server_role == ServerRole.local:
            return func

        # в сервисах декорируем методы
        kwargs.setdefault("noself", True)
        # по дефолту NullSerializer, который не делает копии mutable объектов
        # для создания копии значения используйте PickleSerializer (оверхед на копирование)
        return aiocache(*args, **kwargs)(func)

    return wrapped


class AsyncInitMeta(type):
    async def __call__(cls, *args, **kwargs):
        # Создаем экземпляр класса
        instance = cls.__new__(cls)
        await instance.__ainit__(*args, **kwargs)
        return instance


class Dispatcher[KeyT, ValT, **ParamsT]:
    def __init__(self, key_func):
        self._registry: dict[KeyT, Callable[ParamsT, Awaitable[ValT]]] = {}
        self._default_func: Callable[ParamsT, Awaitable[ValT]] | None = None
        self._key_func: Callable[ParamsT, Awaitable[KeyT]] = key_func

    def register(self, val: KeyT):
        def wrapper(func: Callable[ParamsT, Awaitable[ValT]]):
            if val in self._registry:
                raise ValueError(f"{val} already in registry for {func.__name__}")
            self._registry[val] = func

            return func

        return wrapper

    def register_default(self, func: Callable[ParamsT, Awaitable[ValT]]):
        if self._default_func is not None:
            raise ValueError("Default func is already set")
        self._default_func = func
        return func

    async def dispatch(self, *args: ParamsT.args, **kwargs: ParamsT.kwargs) -> Callable[ParamsT, Awaitable[ValT]]:
        key = await self._key_func(*args, **kwargs)

        if self._default_func is None:
            return self._registry[key]

        return self._registry.get(key) or self._default_func

    async def __call__(self, *args: ParamsT.args, **kwargs: ParamsT.kwargs) -> ValT:
        func = await self.dispatch(*args, **kwargs)
        return await func(*args, **kwargs)


def dispatch_by[KeyT, ValT, **ParamsT](key_func: Callable[ParamsT, Awaitable[KeyT]]) -> Dispatcher[KeyT, ValT, ParamsT]:
    return Dispatcher(key_func)


class MethodDispatcher[KeyT, ValT, SelfT, **ParamsT]:
    def __init__(self, key_func: Callable[Concatenate[SelfT, ParamsT], Awaitable[KeyT]]):
        self._key_func = key_func
        self._registry: dict[KeyT, Callable[Concatenate[SelfT, ParamsT], Awaitable[ValT]]] = {}
        self._default_func: Callable[Concatenate[SelfT, ParamsT], Awaitable[ValT]] | None = None

    def register(self, val: KeyT):
        def wrapper(func: Callable[Concatenate[SelfT, ParamsT], Awaitable[ValT]]):
            if val in self._registry:
                raise ValueError(f"{val} already in registry for {func.__name__}")
            self._registry[val] = func
            return func

        return wrapper

    def register_default(self, func: Callable[Concatenate[SelfT, ParamsT], Awaitable[ValT]]):
        if self._default_func is not None:
            raise ValueError("Default func is already set")
        self._default_func = func
        return func

    def __get__(self, instance: SelfT, owner) -> Callable[ParamsT, Awaitable[ValT]]:
        """Дескриптор для патча метода"""
        if instance is None:
            return self

        async def bound_method(*args: ParamsT.args, **kwargs: ParamsT.kwargs) -> ValT:
            key = await self._key_func(instance, *args, **kwargs)

            if self._default_func is None:
                func = self._registry[key]
            else:
                func = self._registry.get(key) or self._default_func

            result = await func(instance, *args, **kwargs)
            return result

        return bound_method


def method_dispatch[KeyT, ValT, SelfT, **ParamsT](
    func: Callable[Concatenate[SelfT, ParamsT], Awaitable[KeyT]],
) -> MethodDispatcher[KeyT, ValT, SelfT, ParamsT]:
    return MethodDispatcher(func)


def get_socketio_query_param(environ, name) -> str | None:
    query = environ.get("QUERY_STRING", "")
    params = parse_qs(query)
    param_list = params.get(name)
    return param_list and param_list[0] or None


def get_socketio_cookie(environ, name: str):
    raw = environ.get("HTTP_COOKIE", "")
    jar = SimpleCookie()
    jar.load(raw)
    morsel = jar.get(name)
    return morsel.value if morsel else None


def generate_error_responses(cls_name, *errors) -> dict:
    grouped_errors = defaultdict(list)
    for err_cls in errors:
        grouped_errors[err_cls.status_code].append(err_cls)

    responses = {}
    for status_code, error_classes in grouped_errors.items():
        error_codes = (e.error_code for e in error_classes)
        ErrorCodeLiteral = Literal[*error_codes]
        model_name = f"{cls_name}{status_code}"
        dynamic_model = create_model(model_name, error_code=ErrorCodeLiteral, error=str)

        examples = {}
        for err_cls in error_classes:
            examples[err_cls.error_code] = {
                "summary": err_cls.error,
                "value": {
                    "error_code": err_cls.error_code,
                    "error": err_cls.error,
                },
            }

        responses[status_code] = {
            "model": dynamic_model,
            "description": f"Возможные ошибки для статуса {status_code}",
            "content": {"application/json": {"examples": examples}},
        }

    return responses
