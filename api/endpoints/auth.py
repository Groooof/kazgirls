from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from loguru import logger
from sqlalchemy.ext.asyncio.session import AsyncSession

from dependencies import get_db
from dependencies.auth import get_current_active_user
from logic.auth import login_user_by_password
from models import User
from schemas.auth import AccessTokenSchema, LoginSchema
from schemas.user import UserSchema

from ._responses import responses
from ._tags import Tags

router = APIRouter(tags=[Tags.auth_private], responses=responses(status.HTTP_401_UNAUTHORIZED))


@router.post("/login", summary="Идентификация")
async def login_endpoint(
    data: LoginSchema,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AccessTokenSchema:
    logger.debug("Login attempt with data: {}", data)
    token = await login_user_by_password(db, data, response)
    return token


@router.get("/me", summary="Получить информацию о текущем пользователе")
async def get_me_endpoint(
    user: User = Depends(get_current_active_user),
) -> UserSchema:
    user_data = UserSchema(
        id=user.id,
        username=user.username,
        is_superuser=user.is_superuser,
    )
    return user_data
