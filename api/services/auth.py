import datetime

import jwt
from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession

from exceptions.auth import CredentialsException
from models import User, UserSession
from repository.jwt_token import TokenRepository
from repository.user import UserRepository, UserSessionRepository
from schemas.auth import AccessTokenSchema, JWTSessionPayloadSchema, TokenTypesChoices
from services.bases import BaseServiceAbstract
from settings.conf import other_settings
from utils.libs import method_dispatch, utc_now


class AuthTokenService(BaseServiceAbstract):
    # Константы по умолчанию
    COOKIE_NAME = "access_token"
    COOKIE_TTL: int = int(datetime.timedelta(days=30).total_seconds())
    JWT_SECRET_KEY = other_settings.jwt_secret
    ACCESS_TOKEN_EXPIRE = datetime.timedelta(days=30)

    def __init__(self, db: AsyncSession):
        self.user_session = UserSessionRepository(db)
        self.users = UserRepository(db)
        self.jwt_repository = TokenRepository()

    @classmethod
    def _set_access_cookie(cls, response: Response, access_token: str):
        response.set_cookie(
            key=cls.COOKIE_NAME,
            value=access_token,
            httponly=True,
            samesite="strict",
            secure=True,
            max_age=cls.COOKIE_TTL,
        )

    @classmethod
    def _clear_access_cookie(cls, response: Response):
        response.delete_cookie(cls.COOKIE_NAME)

    def _decode_session_token(self, token: str) -> JWTSessionPayloadSchema:
        try:
            payload = self.jwt_repository.decode_token(token, secret_key=self.JWT_SECRET_KEY)
            decoded_payload = JWTSessionPayloadSchema(**payload)
        except jwt.exceptions.PyJWTError:
            raise CredentialsException(message="Invalid token")
        return decoded_payload

    @method_dispatch
    async def create_user_token(
        self,
        user: User,
        payload: dict,
        token_type: TokenTypesChoices,
        response: Response | None = None,
    ) -> TokenTypesChoices:
        return token_type

    @create_user_token.register(TokenTypesChoices.api)
    async def _create_user_api_token(
        self, user: User, payload: dict, token_type: TokenTypesChoices, response: Response | None = None
    ) -> AccessTokenSchema:
        access_token = self.jwt_repository.create_token(payload, self.ACCESS_TOKEN_EXPIRE, self.JWT_SECRET_KEY)
        if response:
            self._set_access_cookie(response, access_token)

        session = UserSession(
            token=access_token,
            user_id=user.id,
            token_type=token_type,
            expired_at=utc_now() + self.ACCESS_TOKEN_EXPIRE,
        )
        await self.user_session.upload_to_storage(session)
        return AccessTokenSchema(access_token=access_token)

    @create_user_token.register(TokenTypesChoices.session)
    async def _create_user_session_token(
        self, user: User, payload: dict, token_type: TokenTypesChoices, response: Response | None = None
    ) -> AccessTokenSchema:
        access_token = self.jwt_repository.create_token(payload, None, self.JWT_SECRET_KEY)
        if response:
            self._set_access_cookie(response, access_token)

        session = UserSession(
            token=access_token,
            user_id=user.id,
            token_type=token_type,
        )
        await self.user_session.upload_to_storage(session)
        return AccessTokenSchema(access_token=access_token)

    async def get_user_by_token(self, token: str, token_type: TokenTypesChoices) -> User:
        self._decode_session_token(token)
        session = await self.user_session.get_active_user_session_by_token(token, token_type)
        if not session:
            raise CredentialsException(message="Invalid token")
        return session.user

    async def deactivate_user_session(self, token: str, response: Response | None = None):
        await self.user_session.deactivate(token)
        if response:
            self._clear_access_cookie(response)
