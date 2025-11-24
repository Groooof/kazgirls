from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from dependencies import get_db, get_redis
from dependencies.auth import get_current_active_user
from logic.lobby import get_free_online_streamers
from models import User
from schemas.lobby import StreamerSchema

from ._responses import responses
from ._tags import Tags

router = APIRouter(tags=[Tags.lobby], responses=responses(status.HTTP_401_UNAUTHORIZED))


@router.get("/streamers", summary="Список свободных стримеров")
async def streamers_endpoint(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: AsyncSession = Depends(get_redis),
) -> list[StreamerSchema]:
    return await get_free_online_streamers(db, redis)
