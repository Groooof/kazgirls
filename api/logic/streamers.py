from datetime import datetime, timedelta

import socketio
from loguru import logger
from redis.asyncio import Redis

from exceptions.streamers import NoSeatsError
from settings.conf import sockets_namespaces
from utils.libs import utc_now


def get_streamer_room_name(streamer_id: int) -> str:
    return f"room_{streamer_id}"


async def connect_streamer(redis: Redis, user_id: int, sid: str) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd("streamers:online", {user_id: now_ts})
    await redis.hset("sids_by_user_id", user_id, sid)


async def connect_viewer(sio: socketio.AsyncServer, redis: Redis, user_id: int, sid: str, streamer_id: int) -> None:
    # TODO: что делать если подключен к другому стримеру?
    now_ts = int(utc_now().timestamp())

    async with redis.lock(f"streamer:{streamer_id}:viewers:lock", timeout=5):
        viewers_ids = await redis.zrange(f"streamers:{streamer_id}:viewers", 0, -1)

        if str(user_id) in viewers_ids:
            room = get_streamer_room_name(streamer_id)
            other_sid = await redis.hget("sids_by_user_id", user_id)
            await sio.emit("disconnect:second_connect", room=room, to=other_sid, namespace=sockets_namespaces.streamers)
            await sio.disconnect(other_sid, sockets_namespaces.streamers)
            await sio.leave_room(other_sid, room, sockets_namespaces.streamers)
        elif len(viewers_ids) >= 1:
            raise NoSeatsError

        await redis.zadd(f"streamers:{streamer_id}:viewers", {user_id: now_ts})
        await redis.hset("sids_by_user_id", user_id, sid)

        viewers_ids = await redis.zrange(f"streamers:{streamer_id}:viewers", 0, -1)
        if len(viewers_ids) >= 1:
            await sio.emit("streamers:busy", {"streamer_id": streamer_id}, namespace=sockets_namespaces.lobby)


async def ping_streamer(redis: Redis, user_id: int) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd("streamers:online", {user_id: now_ts})


async def ping_viewer(redis: Redis, user_id: int, streamer_id: int) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd(f"streamers:{streamer_id}:viewers", {user_id: now_ts})


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
        sid = await redis.hget("sids_by_user_id", viewer_id)

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
