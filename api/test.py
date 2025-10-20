import asyncio

import socketio

sio = socketio.AsyncClient()


@sio.event
async def connect():
    print("✅ Connected")


@sio.event
async def disconnect():
    print("❌ Disconnected")


async def main():
    await sio.connect("http://localhost:8000", namespaces=["/streamers"], auth={"token": "123"})
    await asyncio.sleep(5)
    await sio.disconnect()


asyncio.run(main())
