import datetime

import jwt
from loguru import logger

from exceptions.auth import JWTDecodingError
from repository.bases import BaseRepositoryAbstract
from settings.conf import other_settings
from utils.libs import utc_now


class TokenRepository(BaseRepositoryAbstract):
    async def get(self, *args, **kwargs):
        """return: obj or None."""
        raise NotImplementedError  # pragma: no cover

    async def add(self, *args, **kwargs):
        raise NotImplementedError  # pragma: no cover

    async def update(self, *args, **kwargs):
        raise NotImplementedError  # pragma: no cover

    async def delete(self, *args, **kwargs):
        raise NotImplementedError  # pragma: no cover

    async def first(self, *args, **kwargs):
        """return: FIRST obj or None."""
        raise NotImplementedError  # pragma: no cove

    @classmethod
    def create_token(cls, data: dict, expires_delta: datetime.timedelta | None, secret_key: str) -> str:
        to_encode = data.copy()

        if expires_delta:
            to_encode |= {"exp": utc_now() + expires_delta}
        to_encode |= {"iat": utc_now()}
        token = jwt.encode(to_encode, secret_key, algorithm=other_settings.jwt_algorithm)
        return token

    @classmethod
    def decode_token(cls, token: str, secret_key: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=[other_settings.jwt_algorithm],
                options={"verify_exp": False},  # у сессий нет exp
            )
        except jwt.exceptions.PyJWTError as e:
            logger.exception("Failed to decode JWT token, {}", e)
            raise JWTDecodingError(message="Invalid token")
        return payload
