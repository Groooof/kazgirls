from dependencies.sockets import server as sio

namespace = "/streamers"


@sio.event(namespace=namespace)
async def connect(sid, environ, auth):
    print("Connected:", sid, auth)


@sio.event(namespace=namespace)
async def disconnect(sid):
    print("Disconnected:", sid)
