from datetime import datetime, timedelta

import socketio
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio.session import AsyncSession

from exceptions.bases import Http404
from exceptions.streamers import NoSeatsError
from logic.viewers import _get_viewer_schema_from_obj
from models.streamers import StreamerMark, StreamerProfile
from models.viewers import ViewerProfile
from repository.streamers import StreamerMarkRepository, StreamerProfileRepository
from repository.viewers import ViewerProfileRepository
from schemas.streamers import StreamerSchema, ViewerSchema
from settings.conf import sockets_namespaces
from utils.libs import utc_now


def get_streamer_room_name(streamer_id: int) -> str:
    return f"room_{streamer_id}"


async def connect_streamer(sio: socketio.AsyncServer, redis: Redis, streamer_id: int, sid: str) -> None:
    now_ts = int(utc_now().timestamp())
    room = get_streamer_room_name(streamer_id)

    other_sid = await redis.hget("sids_by_streamer_id", streamer_id)
    if other_sid:
        await sio.emit("disconnect:second_connect", room=room, to=other_sid, namespace=sockets_namespaces.streamers)
        await sio.disconnect(other_sid, sockets_namespaces.streamers)
        await sio.leave_room(other_sid, room, sockets_namespaces.streamers)

    await redis.zadd("streamers:online", {streamer_id: now_ts})
    await redis.hset("sids_by_streamer_id", streamer_id, sid)


async def connect_viewer(sio: socketio.AsyncServer, redis: Redis, viewer_id: int, sid: str, streamer_id: int) -> None:
    # TODO: что делать если подключен к другому стримеру?
    now_ts = int(utc_now().timestamp())

    # TODO: сделать строго один стример - один зритель
    async with redis.lock(f"streamer:{streamer_id}:viewers:lock", timeout=5):
        viewers_ids = await redis.zrange(f"streamers:{streamer_id}:viewers", 0, -1)
        if str(viewer_id) not in viewers_ids and len(viewers_ids) >= 1:
            raise NoSeatsError

        room = get_streamer_room_name(streamer_id)
        other_sid = await redis.hget("sids_by_viewer_id", viewer_id)
        if other_sid:
            await sio.emit("disconnect:second_connect", room=room, to=other_sid, namespace=sockets_namespaces.streamers)
            await sio.disconnect(other_sid, sockets_namespaces.streamers)
            await sio.leave_room(other_sid, room, sockets_namespaces.streamers)

        streamer_sid = await redis.hget("sids_by_streamer_id", streamer_id)
        await redis.zadd(f"streamers:{streamer_id}:viewers", {viewer_id: now_ts})
        await redis.hset("sids_by_viewer_id", viewer_id, sid)
        await sio.emit(
            "viewers:connected",
            {"viewer_id": viewer_id},
            room=room,
            to=streamer_sid,
            namespace=sockets_namespaces.streamers,
        )

        viewers_ids = await redis.zrange(f"streamers:{streamer_id}:viewers", 0, -1)
        if len(viewers_ids) >= 1:
            await sio.emit("streamers:busy", {"streamer_id": streamer_id}, namespace=sockets_namespaces.lobby)


async def ping_streamer(redis: Redis, streamer_id: int) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd("streamers:online", {streamer_id: now_ts})


async def ping_viewer(redis: Redis, viewer_id: int, streamer_id: int) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd(f"streamers:{streamer_id}:viewers", {viewer_id: now_ts})


async def clean_offline_streamers(redis: Redis) -> None:
    max_timestamp = int((utc_now() - timedelta(minutes=2)).timestamp())
    await redis.zremrangebyscore("streamers:online", 0, max_timestamp)


async def clean_streamer_offline_viewers(sio: socketio.AsyncServer, redis: Redis, streamer_id: int) -> None:
    key = f"streamers:{streamer_id}:viewers"
    max_timestamp = int((utc_now() - timedelta(minutes=2)).timestamp())

    active_viewers_ids = []
    viewers_ids = await redis.zrange(key, 0, -1, withscores=True)
    for viewer_id, last_seen_ts in viewers_ids:
        if last_seen_ts > max_timestamp:
            active_viewers_ids.append(viewer_id)
            continue

        last_seen_dt = datetime.fromtimestamp(last_seen_ts)
        logger.info(
            "Disconnecting inactive viewer (id: {}) from streamer (id: {}); last seen {}",
            viewer_id,
            streamer_id,
            last_seen_dt,
        )

        room = get_streamer_room_name(streamer_id)
        sid = await redis.hget("sids_by_viewer_id", viewer_id)

        await sio.emit("disconnect:inactive", room=room, to=sid, namespace=sockets_namespaces.streamers)
        await sio.disconnect(sid, sockets_namespaces.streamers)
        await sio.leave_room(sid, room, sockets_namespaces.streamers)

    await redis.zremrangebyscore(key, 0, max_timestamp)
    if len(active_viewers_ids) < 1:
        await sio.emit("streamers:free", {"streamer_id": streamer_id}, namespace=sockets_namespaces.lobby)


async def clean_offline_viewers(sio: socketio.AsyncServer, redis: Redis) -> None:
    keys = redis.scan_iter("streamers:*:viewers", count=1000)
    async for key in keys:
        _, streamer_id, _ = key.split(":")
        await clean_streamer_offline_viewers(sio, redis, int(streamer_id))


async def get_free_online_streamers_ids(redis: Redis) -> list[int]:
    streamers_ids = await redis.zrange("streamers:online", 0, -1)

    pipe = redis.pipeline()
    [pipe.zrange(f"streamers:{streamer_id}:viewers", 0, -1) for streamer_id in streamers_ids]
    streamers_viewers_ids = await pipe.execute()

    free_streamres_ids = []
    for streamer_id, viewers_ids in zip(streamers_ids, streamers_viewers_ids):
        if len(viewers_ids) < 1:
            free_streamres_ids.append(int(streamer_id))
    return free_streamres_ids


async def get_streamer_viewers_ids(redis: Redis, streamer_id: int) -> list[int]:
    key = f"streamers:{streamer_id}:viewers"
    viewers_ids = await redis.zrange(key, 0, -1)
    return list(map(int, viewers_ids))


async def get_streamer_viewers(db: AsyncSession, redis: Redis, streamer_id: int) -> list[ViewerSchema]:
    viewers_ids = await get_streamer_viewers_ids(redis, streamer_id)
    if not viewers_ids:
        return []

    repo = ViewerProfileRepository(db)
    viewers = await repo.list_(ViewerProfile.id.in_(viewers_ids))
    return [_get_viewer_schema_from_obj(viewer) for viewer in viewers]


async def get_streamer_rating(db: AsyncSession, streamer_id: int) -> tuple[float, int]:
    q = select(
        func.avg(StreamerMark.mark).label("avg_mark"),
    ).where(StreamerMark.streamer_id == streamer_id)

    result = await db.execute(q)
    return result.one()[0]


async def _get_streamer_schema_from_obj(db: AsyncSession, streamer: StreamerProfile) -> StreamerSchema:
    rating = streamer.force_rating or await get_streamer_rating(db, streamer.id)
    rating = rating and round(rating, 2)

    avatar_url = streamer.avatar_url
    return StreamerSchema(id=streamer.id, name=streamer.name, rating=rating, avatar_url=avatar_url)


async def get_free_online_streamers(db: AsyncSession, redis: Redis) -> list[StreamerSchema]:
    streamers_ids = await get_free_online_streamers_ids(redis)
    if not streamers_ids:
        return []

    repo = StreamerProfileRepository(db)
    streamers = await repo.list_(StreamerProfile.id.in_(streamers_ids))
    return [await _get_streamer_schema_from_obj(db, streamer) for streamer in streamers]


async def get_streamer(db: AsyncSession, streamer_id: int) -> StreamerSchema:
    repo = StreamerProfileRepository(db)
    streamer = await repo.first(StreamerProfile.id == streamer_id)
    if not streamer:
        raise Http404

    return await _get_streamer_schema_from_obj(db, streamer)


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
