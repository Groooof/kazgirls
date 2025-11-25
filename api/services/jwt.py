import datetime

import jwt

from services.bases import BaseServiceAbstract
from utils.libs import utc_now


class JwtTokenService(BaseServiceAbstract):
    @classmethod
    def create_token(cls, user_id: int, ttl: datetime.timedelta, secret_key: str) -> str:
        to_encode = {"sub": str(user_id), "iat": utc_now(), "exp": utc_now() + ttl}
        token = jwt.encode(to_encode, secret_key, algorithm="HS256")
        return token

    @classmethod
    def decode_token(cls, token: str, secret_key: str, *, suppress: bool = False) -> dict | None:
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        except (jwt.exceptions.PyJWTError, TypeError):
            if suppress:
                return None
            raise
        return payload
