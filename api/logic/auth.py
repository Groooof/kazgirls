from fastapi import Response
from jwt import ExpiredSignatureError, InvalidSignatureError
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from exceptions.auth import CredentialsException, InvalidTokenError, UserNotFound
from exceptions.db import DoesNotExist
from models.user import User
from schemas.auth import AccessTokenSchema, JWTSessionPayloadSchema, LoginSchema, TokenTypesChoices
from services.auth import AuthTokenService
from services.user import UserService
from utils.auth import verify_password


async def login_user_by_password(db: AsyncSession, data: LoginSchema, response: Response | None) -> AccessTokenSchema:
    user_service = UserService(db=db)

    user = await user_service.get_user_by_username(data.username)

    if not user:
        raise CredentialsException(message="User not found")

    logger.debug("User: id:{} username:{} password:{}", user.id, user.username, user.password)
    if user.username != data.username or not verify_password(data.password, user.password):
        raise CredentialsException(message="Invalid username or password")

    payload = JWTSessionPayloadSchema(
        sub=user.username,
        user_id=user.id,
        token_type=TokenTypesChoices.session,
    )

    token_service = AuthTokenService(db)
    return await token_service.create_user_token(user, payload.model_dump(), payload.token_type, response)


async def logout_user(db: AsyncSession, token: str, response: Response | None = None) -> None:
    token_service = AuthTokenService(db)
    await token_service.deactivate_user_session(token, response)
    return None


async def create_token(db: AsyncSession, response: Response | None, user: User) -> str:
    logger.debug("Creating api access token for user {}", user.username)

    payload = JWTSessionPayloadSchema(
        sub=user.username,
        user_id=user.id,
        token_type=TokenTypesChoices.api,
    )

    user_session_service = AuthTokenService(db)
    tokens = await user_session_service.create_user_token(user, payload.model_dump(), payload.token_type, response)
    return tokens.access_token


async def get_user_by_session_token(db: AsyncSession, token: str) -> User:
    token_service = AuthTokenService(db)
    try:
        user = await token_service.get_user_by_token(token, TokenTypesChoices.session)
    except (InvalidSignatureError, ExpiredSignatureError):
        raise InvalidTokenError
    except DoesNotExist:
        raise UserNotFound
    return user
