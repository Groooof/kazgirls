from loguru import logger
from socketio.exceptions import ConnectionRefusedError as SocketIOConnectionRefusedError
from sqlalchemy.ext.asyncio.session import AsyncSession

from dependencies.db import with_db
from dependencies.sockets import server as sio
from logic.auth import get_user_by_token
from settings.conf import sockets_namespaces

namespace = sockets_namespaces.lobby


@sio.event(namespace=namespace)
@with_db()
async def connect(sid, environ, auth, db: AsyncSession):
    token = auth.get("token")
    user = token and await get_user_by_token(db, token)
    if not user:
        logger.debug("Invalid token {}", token)
        raise SocketIOConnectionRefusedError("INVALID_TOKEN")

    session = {"user": user}
    await sio.save_session(sid, session, namespace)
    await sio.emit("connect:ok", to=sid, namespace=namespace)
    logger.debug("✅ Connected to lobby; id: {}, sid: {}", user.id, sid)
    return True


@sio.event(namespace=namespace)
async def disconnect(sid):
    session = await sio.get_session(sid, namespace)
    user = session["user"]
    logger.debug("Disconnected from lobby; id: {}, sid: {}", user.id, sid)
