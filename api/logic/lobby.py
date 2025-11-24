from redis.asyncio import Redis
from sqlalchemy.ext.asyncio.session import AsyncSession

from models.user import User
from repository.user import UserRepository
from schemas.lobby import StreamerSchema


async def get_free_online_streamers_ids(redis: Redis) -> list[int]:
    streamres_ids = await redis.zrange("streamers:online", 0, -1)

    pipe = redis.pipeline()
    [pipe.zrange(f"streamers:{streamer_id}:viewers", 0, -1) for streamer_id in streamres_ids]
    streamers_viewers_ids = await pipe.execute()

    free_streamres_ids = []
    for streamer_id, viewers_ids in zip(streamres_ids, streamers_viewers_ids):
        if len(viewers_ids) < 1:
            free_streamres_ids.append(int(streamer_id))
    return free_streamres_ids


async def get_free_online_streamers(db: AsyncSession, redis: Redis) -> list[StreamerSchema]:
    streamers_ids = await get_free_online_streamers_ids(redis)

    users_repo = UserRepository(db)
    streamers = await users_repo.list_(User.is_streamer, User.is_active, User.id.in_(streamers_ids))
    return [StreamerSchema(id=streamer.id, name=streamer.name) for streamer in streamers]
