import asyncio

import socketio

sio = socketio.AsyncClient()


# --- стандартные события ---
@sio.event
async def connect():
    print("✅ Connected")


@sio.event
async def disconnect():
    print("❌ Disconnected")


# --- универсальный слушатель: ловит все, что приходит ---
@sio.on("*", namespace="/streamers")
async def catch_all(event, namespace=None, data=None):
    """Будет вызываться для любого события от сервера."""
    print(f"📩 Event: {event}")
    print(f"Namespace: {namespace}")
    print(f"Data: {data}")


@sio.event(namespace="/streamers")
async def connect_error(data):
    print("❌ Ошибка при подключении:", data)


from socketio.exceptions import ConnectionError


async def main():
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiaWF0IjoxNzYxNTA1NjUzLCJleHAiOjE3NjQwOTc2NTN9.RmvpIYfrEFUJPP_w9z0qPQjFrTcPXS0r0yuQXuhuFz4"
    try:
        await sio.connect(
            "http://localhost:8000/?streamer_id=qwerty123",
            namespaces=["/streamers"],
            auth={"token": token},
            transports=["websocket"],
        )
    except ConnectionError:
        print("Ошибка подключения")
        return

    print("👂 Listening for messages...")
    await asyncio.sleep(999999)  # слушаем бесконечно
    await sio.disconnect()


from typing import ClassVar

from redis.asyncio import Redis

from dependencies.redis import with_redis
from utils.libs import utc_now


@with_redis()
async def main2(redis: Redis):
    now_ts = int(utc_now().timestamp())
    await redis.zadd("test:1", {1: now_ts})
    await redis.zadd("test:1", {2: now_ts})
    await redis.zadd("test:1", {3: now_ts})

    now_ts = int(utc_now().timestamp())
    viewers_count = await redis.zrange("test:1", 0, now_ts)
    print(viewers_count)


class BaseError(Exception):
    status: ClassVar[int]
    error_code: ClassVar[str]
    error: ClassVar[str]


class Forbidden(BaseError):
    status = 401
    error_code = "INVALID_TOKEN"
    error = "Доступ запрещен"


class TokenExpired(BaseError):
    status = 401
    error_code = "TOKEN_EXPIRED"
    error = "Срок действия токена истек"


from typing import Literal

from pydantic import BaseModel, create_model


def create_error_model(errors: list[type[BaseError]], model_name: str = "HttpError") -> type[BaseModel]:
    error_codes = [e.error_code for e in errors]
    DynamicErrorCodeEnum = Literal[*error_codes]
    return create_model(model_name, status=int, error_code=DynamicErrorCodeEnum, error=str)


m = create_error_model([Forbidden, TokenExpired])
print(m(status=401, error_code="INVALID_TOKEN2", error="123"))
