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


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
