from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio.session import AsyncSession

from dependencies import get_db
from dependencies.auth import get_current_active_user
from exceptions.auth import WrongCredentials
from exceptions.bases import Http403
from logic.messages import get_messages
from models import User
from schemas.messages import MessageSchema
from utils.libs import generate_error_responses

from ._tags import Tags

router = APIRouter(tags=[Tags.messages])


@router.get(
    "/",
    summary="Сообщения",
    responses=generate_error_responses("GetMessagesEndpointErrors", WrongCredentials, Http403),
)
async def get_messages_endpoint(
    streamer_id: int = Query(..., description="ID стримера"),
    viewer_id: int = Query(..., description="ID зрителя"),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageSchema]:
    if user.streamer_profile.id != streamer_id and user.viewer_profile.id != viewer_id:
        raise Http403
    return await get_messages(db, streamer_id, viewer_id)
