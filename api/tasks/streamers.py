from logic.streamers import clean_offline_streamers
from schemas.jobs import JobContext


async def clean_offline_streamers_task(ctx: JobContext) -> None:
    sio = ctx["sio"]
    redis = ctx["redis_session"]
    await clean_offline_streamers(sio, redis)
