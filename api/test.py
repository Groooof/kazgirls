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


async def main():
    await sio.connect("http://localhost:8000/?room_id=qwerty123", namespaces=["/streamers"], auth={"token": "123"})
    print("👂 Listening for messages...")
    await asyncio.sleep(999999)  # слушаем бесконечно
    await sio.disconnect()


asyncio.run(main())
