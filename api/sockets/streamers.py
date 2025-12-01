import socketio
from loguru import logger
from redis.asyncio import Redis
from socketio.exceptions import ConnectionRefusedError as SocketIOConnectionRefusedError
from sqlalchemy.ext.asyncio.session import AsyncSession

from dependencies.db import with_db
from dependencies.redis import with_redis
from exceptions.streamers import NoSeatsError
from logic.auth import get_user_by_token
from logic.messages import create_message
from logic.streamers import (
    answer_from_streamer,
    connect_streamer,
    ice_from_streamer,
    is_streamer_exists,
    offer_from_streamer,
    ping_streamer,
)
from logic.viewers import answer_from_viewer, connect_viewer, ice_from_viewer, offer_from_viewer, ping_viewer
from settings.conf import other_settings, sockets_namespaces
from utils.libs import get_socketio_cookie as get_cookie, get_socketio_query_param as get_query_param

namespace = sockets_namespaces.streamers


@with_db()
@with_redis()
async def connect(sid, environ, auth, db: AsyncSession, redis: Redis, sio: socketio.AsyncServer):
    token = get_cookie(environ, other_settings.access_token_cookie_name)
    user = token and await get_user_by_token(db, token)
    if not user:
        logger.debug("Invalid token {}", token)
        raise SocketIOConnectionRefusedError("INVALID_TOKEN")

    is_streamer = False
    streamer_id = get_query_param(environ, "streamer_id")
    streamer_id = streamer_id and streamer_id.isdigit() and int(streamer_id) or None
    if not streamer_id:
        if not user.is_streamer:
            logger.debug("Common user (id: {}) tried to connect as streamer", user.id)
            raise SocketIOConnectionRefusedError("FORBIDDEN")
        streamer_id = user.streamer_profile.id
        is_streamer = True
    else:
        if streamer_id == user.streamer_profile.id:
            raise SocketIOConnectionRefusedError("FORBIDDEN")
        if not await is_streamer_exists(db, streamer_id):
            raise SocketIOConnectionRefusedError("NOT_FOUND")

    if is_streamer:
        logger.debug("Connecting streamer (id: {})", user.streamer_profile.id)
        await connect_streamer(sio, redis, user.streamer_profile.id, sid)
    else:
        try:
            logger.debug("Connecting viewer (id: {})", user.viewer_profile.id)
            await connect_viewer(sio, redis, user.viewer_profile.id, sid, streamer_id)
        except NoSeatsError:
            logger.debug(
                "Can`t connect viewer (id: {}) because streamer (id: {}) haven`t seats",
                user.viewer_profile.id,
                streamer_id,
            )
            raise SocketIOConnectionRefusedError("ROOM_FULL")

    session = {"user": user, "streamer_id": streamer_id, "is_streamer": is_streamer}
    await sio.save_session(sid, session, namespace)
    logger.debug("✅ Connected sid: {}", sid)
    return True


async def disconnect(sid, sio: socketio.AsyncServer):
    session = await sio.get_session(sid, namespace)
    user = session.get("user")
    streamer_id = session.get("streamer_id")
    is_streamer = session.get("is_streamer")

    if user:
        if is_streamer:
            logger.debug("Disconnecting streamer (id: {})", user.streamer_profile.id)
        else:
            logger.debug("Disconnecting viewer (id: {}) from streamer (id: {})", user.viewer_profile.id, streamer_id)

    logger.debug("Disconnected sid: {}", sid)


@with_redis()
async def ping(sid, data, redis: Redis, sio: socketio.AsyncServer):
    session = await sio.get_session(sid, namespace)
    user = session["user"]
    streamer_id = session["streamer_id"]
    is_streamer = session["is_streamer"]

    if is_streamer:
        logger.debug("Ping streamer (id: {})", user.id)
        await ping_streamer(redis, user.streamer_profile.id)
    else:
        logger.debug("Ping viewer (id: {}) to streamer (id: {})", user.id, streamer_id)
        await ping_viewer(redis, user.viewer_profile.id)


@with_redis()
async def webrtc_offer(sid, data, sio: socketio.AsyncServer, redis: Redis):
    session = await sio.get_session(sid, namespace)
    user = session["user"]
    is_streamer = session["is_streamer"]

    if is_streamer:
        await offer_from_streamer(sio, redis, user.streamer_profile.id, data)
        logger.debug("offer from streamer (id: {})", user.streamer_profile.id)
    else:
        await offer_from_viewer(sio, redis, user.viewer_profile.id, data)
        logger.debug("offer from viewer (id: {})", user.viewer_profile.id)


@with_redis()
async def webrtc_answer(sid, data, sio: socketio.AsyncServer, redis: Redis):
    session = await sio.get_session(sid, namespace)
    user = session["user"]
    is_streamer = session["is_streamer"]

    if is_streamer:
        await answer_from_streamer(sio, redis, user.streamer_profile.id, data)
        logger.debug("answer from streamer (id: {})", user.streamer_profile.id)
    else:
        await answer_from_viewer(sio, redis, user.viewer_profile.id, data)
        logger.debug("answer from viewer (id: {})", user.viewer_profile.id)


@with_redis()
async def webrtc_ice(sid, data, sio: socketio.AsyncServer, redis: Redis):
    session = await sio.get_session(sid, namespace)
    user = session["user"]
    is_streamer = session["is_streamer"]

    if is_streamer:
        await ice_from_streamer(sio, redis, user.streamer_profile.id, data)
        logger.debug("ice from streamer (id: {})", user.streamer_profile.id)
    else:
        await ice_from_viewer(sio, redis, user.viewer_profile.id, data)
        logger.debug("ice from viewer (id: {})", user.viewer_profile.id)


@with_db()
@with_redis()
async def message(sid, data, sio: socketio.AsyncServer, db: AsyncSession, redis: Redis):
    session = await sio.get_session(sid, namespace)
    streamer_id = session["streamer_id"]
    is_streamer = session["is_streamer"]
    await create_message(sio, db, redis, streamer_id, is_streamer, data["text"])


# NOTE: register new handlers in api/sockets/__init__.py
