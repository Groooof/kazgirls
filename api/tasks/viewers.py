from logic.viewers import clean_offline_viewers
from schemas.jobs import JobContext


async def clean_offline_viewers_task(ctx: JobContext) -> None:
    sio = ctx["sio"]
    redis = ctx["redis_session"]
    await clean_offline_viewers(sio, redis)
