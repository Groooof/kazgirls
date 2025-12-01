import asyncio

import socketio

sio = socketio.AsyncClient()

"""

{
    'streamers:online': {
        1: '2025-12-01 12:39:00',
        2: '2025-12-01 12:35:40',
    },
    'viewers:online': {
        4: '2025-12-01 12:39:00',
        6: '2025-12-01 12:35:40',
    },
    'streamers:viewers': {
        1: 4,
        2: 6,
    },
    'viewers:streamers': {
        4: 1,
        6: 2,
    },
    'streamers:sid': {
        1: adk8fF8c9f,
        2: lFFklffd93,
    },
    'viewers:sid': {
        4: vKV9of091F,
        6: fOd0mfJJ0z,
    },

"""


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
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwiaWF0IjoxNzYyNzExNjg4LCJleHAiOjE3NjUzMDM2ODh9._oX0nQazoczBHDvIGvH06UpfSlYH4o653GZROAfSMcg"
    try:
        await sio.connect(
            "http://localhost:8000/",
            namespaces=["/streamers"],
            auth={"token": token},
            transports=["websocket"],
        )
    except ConnectionError:
        print("Ошибка подключения")
        return

    print("👂 Listening for messages...")
    await sio.emit("message", {"text": "hello!!!"}, namespace="/streamers")

    await asyncio.sleep(999999)  # слушаем бесконечно
    await sio.disconnect()


async def main2():
    from dependencies.db import _get_db
    from dependencies.redis import _get_redis
    from logic.streamers import get_free_online_streamers, get_free_online_streamers_ids

    async with _get_redis() as redis, _get_db() as db:
        r = await get_free_online_streamers_ids(redis)
        r2 = await get_free_online_streamers(db, redis)
        print(r)
        print(r2)


loop = asyncio.get_event_loop()
loop.run_until_complete(main2())
