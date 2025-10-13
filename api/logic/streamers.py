from datetime import timedelta

from redis import Redis

from models.user import User
from utils.libs import utc_now


async def mark_streamer_online(redis: Redis, user: User) -> None:
    await redis.zadd("streamers:online", {user.id, int(utc_now().timestamp)})


async def mark_viewer_online(redis: Redis, user: User, streamer_id: int) -> None:
    # TODO: check_is_busy: bool
    # TODO validate
    await redis.zadd(f"streamers:{streamer_id}:viewers:online", {user.id, int(utc_now().timestamp)})
    viewers_count = await redis.zrange(f"streamers:{streamer_id}:viewers:online", 0, utc_now().timestamp)  # TODO
    if viewers_count >= 1:
        is_busy = await redis.hget(f"streamers:{streamer_id}:data", "is_busy")
        is_busy = bool(int(is_busy))  # TODO: if not exists
        if not is_busy:
            await redis.hset(f"streamers:{streamer_id}:data", "is_busy", "1")


async def clean_offline_streamers(redis: Redis) -> None:
    max_timestamp = (utc_now() - timedelta(minutes=2)).timestamp
    await redis.zremrangebyscore("streamers:online", 0, max_timestamp)


async def clean_offline_viewers(redis: Redis) -> None:
    max_timestamp = (utc_now() - timedelta(minutes=2)).timestamp
    streamers_ids = []  # TODO
    with redis.pipeline() as pipe:
        for streamer_id in streamers_ids:
            pipe.zremrangebyscore(f"streamers:{streamer_id}:viewers:online", 0, max_timestamp)
            pipe.zrange(f"streamers:{streamer_id}:viewers:online", 0, utc_now().timestamp)  # TODO
        _, streamers_viewers_counts = await pipe.execute()

    for streamer_id, viewers_count in zip(streamers_ids, streamers_viewers_counts):
        if viewers_count < 1:
            is_busy = await redis.hget(f"streamers:{streamer_id}:data", "is_busy")
            is_busy = bool(int(is_busy))  # TODO: if not exists
            if is_busy:
                await redis.hset(f"streamers:{streamer_id}:data", "is_busy", 0)
                # TODO: notify not busy
