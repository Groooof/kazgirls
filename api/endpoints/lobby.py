from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio.session import AsyncSession

from dependencies import get_db, get_redis
from dependencies.auth import get_current_active_user
from exceptions.bases import BaseHttpError
from logic.lobby import get_free_online_streamers
from models import User
from schemas.lobby import StreamerSchema
from utils.libs import generate_error_responses

from ._tags import Tags


class Forbidden(BaseHttpError):
    status = 401
    error_code = "INVALID_TOKEN"
    error = "Доступ запрещен"


class TokenExpired(BaseHttpError):
    status = 401
    error_code = "TOKEN_EXPIRED"
    error = "Срок действия токена истек"


router = APIRouter(tags=[Tags.lobby])


@router.get(
    "/streamers",
    summary="Список свободных стримеров",
    responses=generate_error_responses("StreamersEndpointErrors", Forbidden, TokenExpired),
)
async def streamers_endpoint(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: AsyncSession = Depends(get_redis),
) -> list[StreamerSchema]:
    return "asd"
    return await get_free_online_streamers(db, redis)
