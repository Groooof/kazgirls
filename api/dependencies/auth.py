from fastapi import Depends
from fastapi.params import Security
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.db import get_db
from exceptions.auth import CredentialsException, InvalidTokenError
from models.user import User
from schemas.auth import TokenTypesChoices
from services.auth import AuthTokenService

cookie_session = APIKeyCookie(name=AuthTokenService.COOKIE_NAME, auto_error=False)
bearer_token = HTTPBearer(auto_error=False)


async def get_current_active_user(
    session_key: str | None = Security(cookie_session),
    bearer_data: HTTPAuthorizationCredentials | None = Security(bearer_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    logger.debug("Session By Cookies: {}", session_key)
    logger.debug("Session By Header: {}", bearer_data)

    auth_service = AuthTokenService(db)
    if session_key:
        logger.debug("User by session: {}", session_key)
        user = await auth_service.get_user_by_token(session_key, TokenTypesChoices.session)
    elif bearer_data:
        logger.debug("User by bearer: {}", bearer_data)
        user = await auth_service.get_user_by_token(bearer_data.credentials, TokenTypesChoices.api)
    else:
        raise CredentialsException(message="No session key")

    return user


async def get_current_active_superuser(
    session_key: str | None = Security(cookie_session),
    db: AsyncSession = Depends(get_db),
) -> User:
    logger.debug("Session By Cookies: {}", session_key)

    if not session_key:
        raise CredentialsException(message="No session key")

    auth_service = AuthTokenService(db)

    logger.debug("Superuser by session: {}", session_key)
    user = await auth_service.get_user_by_token(session_key, TokenTypesChoices.session)
    if not user.is_superuser:
        raise InvalidTokenError

    return user
