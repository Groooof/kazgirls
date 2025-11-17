from urllib.parse import parse_qs

from loguru import logger
from redis.asyncio import Redis
from socketio.exceptions import ConnectionRefusedError as SocketIOConnectionRefusedError
from sqlalchemy.ext.asyncio.session import AsyncSession

from dependencies.db import with_db
from dependencies.redis import with_redis
from dependencies.sockets import server as sio
from exceptions.streamers import NoSeatsError
from logic.auth import get_user_by_token
from logic.streamers import connect_streamer, connect_viewer, get_streamer_room_name, ping_streamer, ping_viewer
from settings.conf import sockets_namespaces

namespace = sockets_namespaces.streamers


def get_query_param(environ, name) -> str | None:
    query = environ.get("QUERY_STRING", "")
    params = parse_qs(query)
    param_list = params.get(name)
    return param_list and param_list[0] or None


@sio.event(namespace=namespace)
@with_db()
@with_redis()
async def connect(sid, environ, auth, db: AsyncSession, redis: Redis):
    token = auth.get("token")
    user = token and await get_user_by_token(db, token)
    if not user:
        logger.debug("Invalid token {}", token)
        raise SocketIOConnectionRefusedError("INVALID_TOKEN")

    streamer_id = get_query_param(environ, "streamer_id")
    streamer_id = streamer_id and streamer_id.isdigit() and int(streamer_id) or None
    if not streamer_id:
        if not user.is_streamer:
            logger.debug("Common user (id: {}) tried to connect as streamer", user.id)
            raise SocketIOConnectionRefusedError("FORBIDDEN")
        streamer_id = user.id

    is_streamer = streamer_id == user.id
    if is_streamer:
        logger.debug("Connecting streamer (id: {})", user.id)
        await connect_streamer(redis, user, sid)
    else:
        try:
            logger.debug("Connecting viewer (id: {})", user.id)
            await connect_viewer(redis, user, sid, streamer_id)
        except NoSeatsError:
            logger.debug("Can`t connect viewer (id: {}) because streamer (id: {}) haven`t seats", user.id, streamer_id)
            raise SocketIOConnectionRefusedError("ROOM_FULL")

    room = get_streamer_room_name(streamer_id)
    session = {"user": user, "streamer_id": streamer_id, "is_streamer": is_streamer}
    await sio.save_session(sid, session, namespace)
    await sio.enter_room(sid, room, namespace)
    await sio.emit("connect:ok", to=sid, namespace=namespace)
    logger.debug("✅ Connected sid: {}", sid)
    return True


@sio.event(namespace=namespace)
async def disconnect(sid):
    session = await sio.get_session(sid, namespace)
    user = session["user"]
    streamer_id = session["streamer_id"]
    is_streamer = session["is_streamer"]

    if is_streamer:
        logger.debug("Disconnecting streamer (id: {})", user.id)
    else:
        logger.debug("Disconnecting viewer (id: {}) from streamer (id: {})", user.id, streamer_id)

    room = get_streamer_room_name(streamer_id)
    await sio.leave_room(sid, room, namespace)
    logger.debug("Disconnected sid: {}", sid)


@sio.event(namespace=namespace)
@with_redis()
async def ping(sid, data, redis: Redis):
    session = await sio.get_session(sid, namespace)
    user = session["user"]
    streamer_id = session["streamer_id"]
    is_streamer = session["is_streamer"]

    if is_streamer:
        logger.debug("Ping streamer (id: {})", user.id)
        await ping_streamer(redis, user)
    else:
        logger.debug("Ping viewer (id: {}) to streamer (id: {})", user.id, streamer_id)
        await ping_viewer(redis, user, streamer_id)


@sio.on("webrtc:offer", namespace=namespace)
async def webrtc_offer(sid, data):
    session = await sio.get_session(sid, namespace)
    user = session["user"]
    streamer_id = session["streamer_id"]
    is_streamer = session["is_streamer"]

    if is_streamer:
        logger.debug("offer from streamer (id: {})", user.id)
    else:
        logger.debug("offer from viewer (id: {})", user.id)

    room = get_streamer_room_name(streamer_id)
    await sio.emit("webrtc:offer", data, room=room, skip_sid=sid, namespace=namespace)


@sio.on("webrtc:answer", namespace=namespace)
async def webrtc_answer(sid, data):
    session = await sio.get_session(sid, namespace)
    user = session["user"]
    streamer_id = session["streamer_id"]
    is_streamer = session["is_streamer"]

    if is_streamer:
        logger.debug("answer from streamer (id: {})", user.id)
    else:
        logger.debug("answer from viewer (id: {})", user.id)

    room = get_streamer_room_name(streamer_id)
    await sio.emit("webrtc:answer", data, room=room, skip_sid=sid, namespace=namespace)


@sio.on("webrtc:ice", namespace=namespace)
async def webrtc_ice(sid, data):
    session = await sio.get_session(sid, namespace)
    user = session["user"]
    streamer_id = session["streamer_id"]
    is_streamer = session["is_streamer"]

    if is_streamer:
        logger.debug("ice from streamer (id: {})", user.id)
    else:
        logger.debug("ice from viewer (id: {})", user.id)

    room = get_streamer_room_name(streamer_id)
    await sio.emit("webrtc:ice", data, room=room, skip_sid=sid, namespace=namespace)
