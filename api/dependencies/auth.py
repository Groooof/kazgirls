from fastapi import Depends
from fastapi.params import Security
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.db import get_db
from exceptions.auth import CredentialsException
from models.user import User
from services.auth import UserSessionService
from services.jwt import JwtTokenService
from settings import conf

cookie_session = APIKeyCookie(name=conf.other_settings.access_token_cookie_name, auto_error=False)


async def get_access_token(token: str | None = Security(cookie_session)) -> str:
    if not token:
        raise CredentialsException(message="No access token")

    jwt_service = JwtTokenService()
    payload = jwt_service.decode_token(token, conf.other_settings.jwt_secret, suppress=True)
    if not payload:
        raise CredentialsException(message="Invalid token")

    return token


async def get_current_active_user(db: AsyncSession = Depends(get_db), token: str = Depends(get_access_token)) -> User:
    session_service = UserSessionService(db)
    user = await session_service.get_user(token)
    if not user:
        raise CredentialsException(message="Invalid token")
    return user
