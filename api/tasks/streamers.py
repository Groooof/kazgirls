from logic.streamers import clean_offline_streamers, clean_offline_viewers
from schemas.jobs import JobContext


async def clean_offline_streamers_task(ctx: JobContext) -> None:
    redis = ctx["redis_session"]
    await clean_offline_streamers(redis)


async def clean_offline_viewers_task(ctx: JobContext) -> None:
    sio = ctx["sio"]
    redis = ctx["redis_session"]
    await clean_offline_viewers(sio, redis)
