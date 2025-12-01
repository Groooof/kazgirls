from datetime import timedelta

import socketio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio.session import AsyncSession

from exceptions.bases import Http404
from exceptions.streamers import NoSeatsError
from models.viewers import ViewerProfile
from repository.viewers import ViewerProfileRepository
from schemas.streamers import ViewerSchema
from settings.conf import sockets_namespaces as namespaces
from utils.libs import utc_now


async def disconnect_viewer(sio: socketio.AsyncServer, redis: Redis, viewer_id: int, reason: str) -> None:
    async with redis.lock(f"viewers:{viewer_id}:disconnect:lock", timeout=5):
        pipe = redis.pipeline()
        pipe.hget("viewers:sid", viewer_id)
        pipe.hget("viewers:streamers", viewer_id)
        sid, streamer_id = await pipe.execute()

        if sid:
            pipe = redis.pipeline()
            pipe.zrem("viewers:online", viewer_id)
            pipe.hdel("viewers:sid", viewer_id)
            pipe.hdel("streamers:viewers", streamer_id)
            pipe.hdel("viewers:streamers", viewer_id)
            pipe.hget("streamers:sid", streamer_id)
            *_, streamer_sid = await pipe.execute()

            await sio.emit("streamers:free", {"streamer_id": streamer_id}, namespace=namespaces.lobby)
            await sio.emit("viewers:disconnected", {"reason": reason}, to=sid, namespace=namespaces.streamers)
            await sio.emit("viewers:disconnected", {"reason": reason}, to=streamer_sid, namespace=namespaces.streamers)
            await sio.disconnect(sid, namespaces.streamers)


async def connect_viewer(sio: socketio.AsyncServer, redis: Redis, viewer_id: int, sid: str, streamer_id: int) -> None:
    async with redis.lock(f"streamer:{streamer_id}:viewers:lock", timeout=5):
        connected_viewer_id = await redis.hget("streamers:viewers", streamer_id)
        if connected_viewer_id and connected_viewer_id != str(viewer_id):
            raise NoSeatsError

        await disconnect_viewer(sio, redis, viewer_id, "second_connect")

        now_ts = int(utc_now().timestamp())
        pipe = redis.pipeline()
        pipe.zadd("viewers:online", {viewer_id: now_ts})
        pipe.hset("viewers:sid", viewer_id, sid)
        pipe.hset("streamers:viewers", streamer_id, viewer_id)
        pipe.hset("viewers:streamers", viewer_id, streamer_id)
        pipe.hget("streamers:sid", streamer_id)
        *_, streamer_sid = await pipe.execute()

        await sio.emit("streamers:busy", {"streamer_id": streamer_id}, namespace=namespaces.lobby)
        await sio.emit("viewers:connected", {"viewer_id": viewer_id}, to=streamer_sid, namespace=namespaces.streamers)
        await sio.emit("viewers:connected", to=sid, namespace=namespaces.streamers)


async def ping_viewer(redis: Redis, viewer_id: int) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd("viewers:online", {viewer_id: now_ts})


async def offer_from_viewer(sio: socketio.AsyncServer, redis: Redis, viewer_id: int, data: dict) -> None:
    streamer_id = await redis.hget("viewers:streamers", viewer_id)
    streamer_sid = await redis.hget("streamers:sid", streamer_id)
    await sio.emit("webrtc:offer", data, to=streamer_sid, namespace=namespaces.streamers)


async def answer_from_viewer(sio: socketio.AsyncServer, redis: Redis, viewer_id: int, data: dict) -> None:
    streamer_id = await redis.hget("viewers:streamers", viewer_id)
    streamer_sid = await redis.hget("streamers:sid", streamer_id)
    await sio.emit("webrtc:answer", data, to=streamer_sid, namespace=namespaces.streamers)


async def ice_from_viewer(sio: socketio.AsyncServer, redis: Redis, viewer_id: int, data: dict) -> None:
    streamer_id = await redis.hget("viewers:streamers", viewer_id)
    streamer_sid = await redis.hget("streamers:sid", streamer_id)
    await sio.emit("webrtc:ice", data, to=streamer_sid, namespace=namespaces.streamers)


async def clean_offline_viewers(sio: socketio.AsyncServer, redis: Redis) -> None:
    max_timestamp = int((utc_now() - timedelta(minutes=2)).timestamp())
    viewers_ids = await redis.zrangebyscore("viewers:online", 0, max_timestamp)
    for viewer_id in viewers_ids:
        await disconnect_viewer(sio, redis, viewer_id, "inactive")


def serialize_viewer(viewer: ViewerProfile) -> ViewerSchema:
    return ViewerSchema(id=viewer.id, name=viewer.name)


async def get_viewer(db: AsyncSession, viewer_id: int) -> ViewerSchema:
    repo = ViewerProfileRepository(db)
    viewer = await repo.first(ViewerProfile.id == viewer_id)
    if not viewer:
        raise Http404

    return serialize_viewer(viewer)


async def get_streamer_viewer(db: AsyncSession, redis: Redis, streamer_id: int) -> ViewerSchema:
    viewer_id = await redis.hget("streamers:viewers", streamer_id)
    if not viewer_id:
        raise Http404

    return await get_viewer(db, viewer_id)
