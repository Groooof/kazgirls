from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio.session import AsyncSession

from dependencies import get_db, get_redis
from dependencies.auth import get_current_active_user
from exceptions.auth import WrongCredentials
from exceptions.bases import Http403, Http404
from logic.streamers import get_free_online_streamers, get_streamer, get_streamer_viewers, rate_streamer
from models import User
from schemas.streamers import StreamerMarkSchema, StreamerSchema, ViewerSchema
from utils.libs import generate_error_responses

from ._tags import Tags

router = APIRouter(tags=[Tags.streamers])


@router.get(
    "/",
    summary="Список свободных стримеров",
    responses=generate_error_responses("GetFreeOnlineStreamersEndpointErrors", WrongCredentials),
)
async def get_free_online_streamers_endpoint(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: AsyncSession = Depends(get_redis),
) -> list[StreamerSchema]:
    return await get_free_online_streamers(db, redis)


@router.get(
    "/me",
    summary="Профиль стримера текущего пользователя",
    responses=generate_error_responses("GetCurrentStreamerEndpointErrors", WrongCredentials, Http404, Http403),
)
async def get_current_streamer_endpoint(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StreamerSchema:
    if not user.is_streamer:
        raise Http403
    return await get_streamer(db, user.streamer_profile.id)


@router.get(
    "/{streamer_id}",
    summary="Информация о стримере",
    responses=generate_error_responses("GetStreamerEndpointErrors", WrongCredentials, Http404),
)
async def get_streamer_endpoint(
    streamer_id: int,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StreamerSchema:
    return await get_streamer(db, streamer_id)


@router.post(
    "/{streamer_id}/rate",
    summary="Поставить оценку стримеру",
    responses=generate_error_responses("RateStreamerEndpointErrors", WrongCredentials, Http404),
)
async def rate_streamer_endpoint(
    streamer_id: int,
    data: StreamerMarkSchema,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await rate_streamer(db, user.viewer_profile.id, data.mark, streamer_id)


@router.get(
    "/{streamer_id}/viewers",
    summary="Информация о зрителях стримера",
    responses=generate_error_responses("GetStreamerViewersEndpointErrors", WrongCredentials),
)
async def get_streamer_viewers_endpoint(
    streamer_id: int,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[ViewerSchema]:
    return await get_streamer_viewers(db, streamer_id)
