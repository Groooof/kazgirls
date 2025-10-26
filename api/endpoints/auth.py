from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from loguru import logger
from sqlalchemy.ext.asyncio.session import AsyncSession

from dependencies import get_db
from dependencies.auth import get_access_token, get_current_active_user
from logic.auth import login_user_by_password, logout_user
from models import User
from schemas.auth import LoginRequestSchema, LoginResponseSchema
from schemas.user import UserSchema
from settings import conf

from ._responses import responses
from ._tags import Tags

router = APIRouter(tags=[Tags.auth_private], responses=responses(status.HTTP_401_UNAUTHORIZED))


@router.post("/login", summary="Аутентификация")
async def login_endpoint(
    data: LoginRequestSchema,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponseSchema:
    logger.debug("Login attempt with data: {}", data)
    token = await login_user_by_password(db, data.username, data.password)
    response.set_cookie(
        key=conf.other_settings.access_token_cookie_name,
        value=token,
        httponly=True,
        samesite="strict",
        secure=True,
        max_age=int(conf.other_settings.users_session_ttl.total_seconds()),
    )
    return LoginResponseSchema(access_token=token)


@router.post("/logout", summary="Логаут")
async def logout_endpoint(
    response: Response,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_access_token),
) -> None:
    await logout_user(db, token)
    response.delete_cookie(
        key=conf.other_settings.access_token_cookie_name,
        httponly=True,
        samesite="strict",
        secure=True,
    )


@router.get("/me", summary="Получить информацию о текущем пользователе")
async def get_me_endpoint(
    user: User = Depends(get_current_active_user),
) -> UserSchema:
    user_data = UserSchema(
        id=user.id,
        username=user.username,
        is_streamer=user.is_streamer,
        is_superuser=user.is_superuser,
    )
    return user_data
