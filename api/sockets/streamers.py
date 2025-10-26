from urllib.parse import parse_qs

from socketio.exceptions import ConnectionRefusedError as SocketIOConnectionRefusedError

from dependencies.db import with_db
from dependencies.sockets import server as sio
from logic.auth import get_user_by_token

namespace = "/streamers"


def get_query_param(environ, name) -> str | None:
    query = environ.get("QUERY_STRING", "")
    params = parse_qs(query)
    param_list = params.get(name)
    return param_list and param_list[0] or None


def get_room_name(streamer_id: str) -> str:
    return f"room_{streamer_id}"


@sio.event(namespace=namespace)
@with_db()
async def connect(sid, environ, auth, db):
    streamer_id = get_query_param(environ, "streamer_id")
    if not streamer_id:
        raise ConnectionRefusedError("NO_STREAMER_ID")

    token = auth.get("token")
    user = token and await get_user_by_token(db, token)
    if not user:
        raise SocketIOConnectionRefusedError("INVALID_TOKEN")

    print(user)

    room_name = get_room_name(streamer_id)
    session = {"user": user, "streamer_id": streamer_id}
    await sio.save_session(sid, session, namespace)
    await sio.enter_room(sid, room_name, namespace=namespace)
    await sio.emit("connect:ok", to=sid, namespace=namespace)
    print(f"✅ Connected {sid} -> room {room_name}")
    return True


@sio.event(namespace=namespace)
async def disconnect(sid):
    print("Disconnected:", sid)
    session = await sio.get_session(sid, namespace)
    if session:
        room_name = get_room_name(session["streamer_id"])
        await sio.leave_room(sid, room_name, namespace=namespace)
        print(f"Left room {room_name}")


# ----------  WEBRTC SIGNALING  ----------
@sio.on("webrtc:offer", namespace=namespace)
async def webrtc_offer(sid, data):
    session = await sio.get_session(sid, namespace)
    room_name = get_room_name(session["streamer_id"])
    print(f"[OFFER] from {sid} -> {room_name}")
    await sio.emit("webrtc:offer", data, room=room_name, skip_sid=sid, namespace=namespace)


@sio.on("webrtc:answer", namespace=namespace)
async def webrtc_answer(sid, data):
    session = await sio.get_session(sid, namespace)
    room_name = get_room_name(session["streamer_id"])
    print(f"[ANSWER] from {sid} -> {room_name}")
    await sio.emit("webrtc:answer", data, room=room_name, skip_sid=sid, namespace=namespace)


@sio.on("webrtc:ice", namespace=namespace)
async def webrtc_ice(sid, data):
    session = await sio.get_session(sid, namespace)
    room = f"room_{session['streamer_id']}"
    print(f"[ICE] from {sid} -> {room}")
    await sio.emit("webrtc:ice", data, room=room, skip_sid=sid, namespace=namespace)
