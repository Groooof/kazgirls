from datetime import timedelta

import socketio
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio.session import AsyncSession

from exceptions.bases import Http404
from models.streamers import StreamerMark, StreamerProfile
from repository.streamers import StreamerMarkRepository, StreamerProfileRepository
from schemas.streamers import StreamerSchema
from settings.conf import sockets_namespaces as namespaces
from utils.libs import utc_now


async def disconnect_streamer(sio: socketio.AsyncServer, redis: Redis, streamer_id: int, reason: str) -> None:
    async with redis.lock(f"streamers:{streamer_id}:disconnect:lock", timeout=5):
        pipe = redis.pipeline()
        pipe.hget("streamers:sid", streamer_id)
        pipe.hget("streamers:viewers", streamer_id)
        sid, viewer_id = await pipe.execute()
        viewer_id = viewer_id or "0"

        if sid:
            pipe = redis.pipeline()
            pipe.zrem("streamers:online", streamer_id)
            pipe.hdel("streamers:sid", streamer_id)
            pipe.hget("viewers:sid", viewer_id)
            *_, viewer_sid = await pipe.execute()

            if viewer_sid:
                await sio.emit(
                    "streamers:disconnected", {"reason": reason}, to=viewer_sid, namespace=namespaces.streamers
                )
            await sio.emit("streamers:disconnected", {"reason": reason}, to=sid, namespace=namespaces.streamers)
            await sio.emit("streamers:disconnected", {"streamer_id": streamer_id}, namespace=namespaces.lobby)
            await sio.disconnect(sid, namespaces.streamers)


async def connect_streamer(sio: socketio.AsyncServer, redis: Redis, streamer_id: int, sid: str) -> None:
    async with redis.lock(f"streamers:{streamer_id}:connect:lock", timeout=5):
        await disconnect_streamer(sio, redis, streamer_id, "second_connect")

        now_ts = int(utc_now().timestamp())
        pipe = redis.pipeline()
        pipe.zadd("streamers:online", {streamer_id: now_ts})
        pipe.hset("streamers:sid", streamer_id, sid)
        await pipe.execute()

        await sio.emit("streamers:connected", {"streamer_id": streamer_id}, namespace=namespaces.lobby)
        await sio.emit("streamers:connected", to=sid, namespace=namespaces.lobby)


async def ping_streamer(redis: Redis, streamer_id: int) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd("streamers:online", {streamer_id: now_ts})


async def offer_from_streamer(sio: socketio.AsyncServer, redis: Redis, streamer_id: int, data: dict) -> None:
    viewer_id = await redis.hget("streamers:viewers", streamer_id)
    viewer_sid = await redis.hget("viewers:sid", viewer_id)
    await sio.emit("webrtc:offer", data, to=viewer_sid, namespace=namespaces.streamers)


async def answer_from_streamer(sio: socketio.AsyncServer, redis: Redis, streamer_id: int, data: dict) -> None:
    viewer_id = await redis.hget("streamers:viewers", streamer_id)
    viewer_sid = await redis.hget("viewers:sid", viewer_id)
    await sio.emit("webrtc:answer", data, to=viewer_sid, namespace=namespaces.streamers)


async def ice_from_streamer(sio: socketio.AsyncServer, redis: Redis, streamer_id: int, data: dict) -> None:
    viewer_id = await redis.hget("streamers:viewers", streamer_id)
    viewer_sid = await redis.hget("viewers:sid", viewer_id)
    await sio.emit("webrtc:ice", data, to=viewer_sid, namespace=namespaces.streamers)


async def clean_offline_streamers(sio: socketio.AsyncServer, redis: Redis) -> None:
    max_timestamp = int((utc_now() - timedelta(minutes=2)).timestamp())
    streamers_ids = await redis.zrangebyscore("streamers:online", 0, max_timestamp)
    for streamer_id in streamers_ids:
        await disconnect_streamer(sio, redis, streamer_id, "inactive")


async def get_streamer_rating(db: AsyncSession, streamer_id: int) -> tuple[float, int]:
    q = select(
        func.avg(StreamerMark.mark).label("avg_mark"),
    ).where(StreamerMark.streamer_id == streamer_id)

    result = await db.execute(q)
    return result.one()[0]


async def serialize_streamer(db: AsyncSession, streamer: StreamerProfile) -> StreamerSchema:
    rating = streamer.force_rating or await get_streamer_rating(db, streamer.id)
    rating = rating and round(rating, 2)

    avatar_url = streamer.avatar_url
    return StreamerSchema(id=streamer.id, name=streamer.name, rating=rating, avatar_url=avatar_url)


async def get_streamer(db: AsyncSession, redis: Redis, streamer_id: int) -> StreamerSchema:
    repo = StreamerProfileRepository(db)
    streamer = await repo.first(StreamerProfile.id == streamer_id)
    if not streamer:
        raise Http404

    return await serialize_streamer(db, streamer)


async def get_free_online_streamers_ids(redis: Redis) -> list[int]:
    pipe = redis.pipeline()
    pipe.zrange("streamers:online", 0, -1)
    pipe.hkeys("streamers:viewers")
    online_streamers_ids, busy_streamers_ids = await pipe.execute()
    return list(map(int, set(online_streamers_ids) - set(busy_streamers_ids)))


async def get_free_online_streamers(db: AsyncSession, redis: Redis) -> list[StreamerSchema]:
    streamers_ids = await get_free_online_streamers_ids(redis)
    if not streamers_ids:
        return []

    repo = StreamerProfileRepository(db)
    streamers = await repo.list_(StreamerProfile.id.in_(streamers_ids))
    return [await serialize_streamer(db, streamer) for streamer in streamers]


async def rate_streamer(db: AsyncSession, viewer_id: int, mark: int, streamer_id: int) -> None:
    repo = StreamerProfileRepository(db)
    streamer_exists = await repo.exists(StreamerProfile.id == streamer_id)
    if not streamer_exists:
        raise Http404

    streamers_marks_repo = StreamerMarkRepository(db)
    await streamers_marks_repo.update_or_create(
        {"mark": mark},
        viewer_id=viewer_id,
        streamer_id=streamer_id,
    )


async def is_streamer_exists(db: AsyncSession, streamer_id: int) -> bool:
    repo = StreamerProfileRepository(db)
    return await repo.exists(StreamerProfile.id == streamer_id)
