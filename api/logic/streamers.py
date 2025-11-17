from datetime import datetime, timedelta

import socketio
from loguru import logger
from redis.asyncio import Redis

from exceptions.streamers import NoSeatsError
from models.user import User
from settings.conf import sockets_namespaces
from utils.libs import utc_now


def get_streamer_room_name(streamer_id: int) -> str:
    return f"room_{streamer_id}"


async def connect_streamer(redis: Redis, user: User, sid: str) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd("streamers:online", {user.id: now_ts})
    await redis.hset("sids_by_user_id", user.id, sid)


async def connect_viewer(sio: socketio.AsyncServer, redis: Redis, user: User, sid: str, streamer_id: int) -> None:
    now_ts = int(utc_now().timestamp())
    viewers_ids = await redis.zrange(f"streamers:{streamer_id}:viewers", 0, now_ts)
    if len(viewers_ids) >= 1 and str(user.id) not in viewers_ids:
        raise NoSeatsError

    # TODO: maybe disconnect other user socket
    await redis.zadd(f"streamers:{streamer_id}:viewers", {user.id: now_ts})
    await redis.hset("sids_by_user_id", user.id, sid)

    if len(viewers_ids) + 1 >= 1:
        await sio.emit("streamers:busy", {"streamer_id": streamer_id}, namespace=sockets_namespaces.lobby)


async def ping_streamer(redis: Redis, user: User) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd("streamers:online", {user.id: now_ts})


async def ping_viewer(redis: Redis, user: User, streamer_id: int) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd(f"streamers:{streamer_id}:viewers", {user.id: now_ts})


async def clean_offline_streamers(redis: Redis) -> None:
    max_timestamp = (utc_now() - timedelta(minutes=2)).timestamp()
    await redis.zremrangebyscore("streamers:online", 0, max_timestamp)


async def clean_streamer_offline_viewers(sio: socketio.AsyncServer, redis: Redis, streamer_id: int) -> None:
    # TODO: lock?
    now_ts = utc_now()
    key = f"streamers:{streamer_id}:viewers"
    max_timestamp = (now_ts - timedelta(minutes=2)).timestamp()

    active_viewers_ids = []
    viewers_ids = await redis.zrange(key, 0, now_ts, withscores=True)
    for viewer_id, last_seen_ts in viewers_ids:
        if last_seen_ts >= max_timestamp:
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

        await sio.disconnect(sid, sockets_namespaces.streamers)
        await sio.leave_room(sid, room, sockets_namespaces.streamers)

    await redis.zremrangebyscore(key, 0, max_timestamp)
    if active_viewers_ids < 1:
        await sio.emit("streamers:free", {"streamer_id": streamer_id}, namespace=sockets_namespaces.lobby)


async def clean_offline_viewers(sio: socketio.AsyncServer, redis: Redis) -> None:
    keys = redis.scan_iter("streamers:*:viewers", count=100)
    async for key in keys:
        _, streamer_id, _ = key.split(":")
        await clean_streamer_offline_viewers(sio, redis, int(streamer_id))
