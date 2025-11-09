from datetime import timedelta

from redis.asyncio import Redis

from exceptions.streamers import NoSeatsError
from models.user import User
from utils.libs import utc_now


async def connect_streamer(redis: Redis, user: User, sid: str) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd("streamers:online", {user.id: now_ts})
    await redis.hset("user_ids_by_sid", sid, user.id)


async def connect_viewer(redis: Redis, user: User, sid: str, streamer_id: int) -> None:
    now_ts = int(utc_now().timestamp())
    viewers_ids = await redis.zrange(f"streamers:{streamer_id}:viewers", 0, now_ts)
    if len(viewers_ids) >= 1 and str(user.id) not in viewers_ids:
        raise NoSeatsError

    await redis.zadd(f"streamers:{streamer_id}:viewers", {user.id: now_ts})
    await redis.hset("user_ids_by_sid", sid, user.id)


async def ping_streamer(redis: Redis, user: User) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd("streamers:online", {user.id: now_ts})


async def ping_viewer(redis: Redis, user: User, streamer_id: int) -> None:
    now_ts = int(utc_now().timestamp())
    await redis.zadd(f"streamers:{streamer_id}:viewers", {user.id: now_ts})


async def clean_offline_streamers(redis: Redis) -> None:
    max_timestamp = (utc_now() - timedelta(minutes=2)).timestamp()
    await redis.zremrangebyscore("streamers:online", 0, max_timestamp)


async def clean_offline_viewers(redis: Redis) -> None:
    max_timestamp = (utc_now() - timedelta(minutes=2)).timestamp()
    streamers_ids = []  # TODO
    with redis.pipeline() as pipe:
        for streamer_id in streamers_ids:
            pipe.zremrangebyscore(f"streamers:{streamer_id}:viewers:online", 0, max_timestamp)
            pipe.zrange(f"streamers:{streamer_id}:viewers:online", 0, utc_now().timestamp())  # TODO
        _, streamers_viewers_counts = await pipe.execute()

    for streamer_id, viewers_count in zip(streamers_ids, streamers_viewers_counts):
        if viewers_count < 1:
            is_busy = await redis.hget(f"streamers:{streamer_id}:data", "is_busy")
            is_busy = bool(int(is_busy))  # TODO: if not exists
            if is_busy:
                await redis.hset(f"streamers:{streamer_id}:data", "is_busy", 0)
                # TODO: notify not busy
