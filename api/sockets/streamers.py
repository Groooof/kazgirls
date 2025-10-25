from urllib.parse import parse_qs

from dependencies.sockets import server as sio

namespace = "/streamers"


def get_query_param(environ, name) -> str | None:
    query = environ.get("QUERY_STRING", "")
    params = parse_qs(query)
    param_list = params.get(name)
    return param_list and param_list[0] or None


def get_room_name(streamer_id: str) -> str:
    return f"room_{streamer_id}"


@sio.event(namespace=namespace)
async def connect(sid, environ, auth):
    streamer_id = get_query_param(environ, "streamer_id")
    if not streamer_id:
        await sio.emit("connect:error", to=sid, namespace=namespace)
        await sio.disconnect(sid, namespace=namespace)  # ?
        return False

    room_name = get_room_name(streamer_id)
    await sio.save_session(sid, {"streamer_id": streamer_id}, namespace)
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
