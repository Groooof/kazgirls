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
            headers={"Cookie": "csrftoken=NtiymjcJsSFuAjo40mRDlqP2alwwuohF;"},
        )
    except ConnectionError:
        print("Ошибка подключения")
        return

    print("👂 Listening for messages...")
    await asyncio.sleep(999999)  # слушаем бесконечно
    await sio.disconnect()


asyncio.run(main())
