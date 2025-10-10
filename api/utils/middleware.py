import tracemalloc

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TracemallocMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Take snapshot before request
        snapshot1 = tracemalloc.take_snapshot()

        response = await call_next(request)

        # Take snapshot after request
        snapshot2 = tracemalloc.take_snapshot()

        # Get memory differences
        top_stats = snapshot2.compare_to(snapshot1, "lineno")

        # Log top 5 memory differences if significant
        if top_stats and top_stats[0].size_diff > 1024 * 1024:  # Only log if diff > 1MB
            logger.debug("Memory usage for {}:", request.url.path)
            for stat in top_stats[:5]:
                logger.debug(stat)

        return response
