from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from exceptions.auth import CredentialsException
from models.user import User
from services.auth import UserSessionService
from services.jwt import JwtTokenService
from services.user import UserService
from settings import conf
from utils.auth import verify_password


async def login_user_by_password(db: AsyncSession, username: str, password: str) -> str:
    user_service = UserService(db)
    session_service = UserSessionService(db)
    jwt_service = JwtTokenService()

    user = await user_service.get_user_by_username(username)
    if not user:
        raise CredentialsException(message="User not found")

    logger.debug("User: id:{} username:{} password:{}", user.id, user.username, user.password)
    if user.username != username or not verify_password(password, user.password):
        raise CredentialsException(message="Invalid username or password")

    token = jwt_service.create_token(user.id, conf.other_settings.users_session_ttl, conf.other_settings.jwt_secret)
    await session_service.create_session(user.id, token, conf.other_settings.users_session_ttl)
    return token


async def logout_user(db: AsyncSession, token: str) -> None:
    session_service = UserSessionService(db)
    await session_service.deactivate_session(token)


async def get_user_by_token(db: AsyncSession, token: str) -> User | None:
    jwt_service = JwtTokenService()
    payload = jwt_service.decode_token(token, conf.other_settings.jwt_secret, suppress=True)
    if not payload:
        return None

    session_service = UserSessionService(db)
    user = await session_service.get_user(token)
    if not user:
        return None
    return user
