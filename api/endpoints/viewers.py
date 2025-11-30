from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio.session import AsyncSession

from dependencies import get_db
from dependencies.auth import get_current_active_user
from exceptions.auth import WrongCredentials
from exceptions.bases import Http404
from logic.viewers import get_viewer
from models import User
from schemas.streamers import ViewerSchema
from utils.libs import generate_error_responses

from ._tags import Tags

router = APIRouter(tags=[Tags.viewers])


@router.get(
    "/me",
    summary="Профиль зрителя текущего пользователя",
    responses=generate_error_responses("GetCurrentViewerEndpointErrors", WrongCredentials, Http404),
)
async def get_current_viewer_endpoint(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ViewerSchema:
    return await get_viewer(db, user.viewer_profile.id)


@router.get(
    "/{viewer_id}",
    summary="Информация о зрителе",
    responses=generate_error_responses("GetViewerEndpointErrors", WrongCredentials, Http404),
)
async def get_viewer_endpoint(
    viewer_id: int,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ViewerSchema:
    return await get_viewer(db, viewer_id)
