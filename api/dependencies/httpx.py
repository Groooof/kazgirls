from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager as asynccontextmanager

from httpx import AsyncClient


async def get_httpx_client() -> AsyncGenerator[AsyncClient]:
    async with AsyncClient() as client:
        yield client


@asynccontextmanager
async def _get_httpx_client() -> AsyncGenerator[AsyncClient]:
    client = AsyncClient()
    try:
        yield client
    finally:
        await client.aclose()
