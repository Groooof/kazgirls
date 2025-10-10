from arq import ArqRedis
from fastapi import Request


async def get_task_manager(request: Request) -> ArqRedis:
    return request.app.state.arq_pool
