from fastapi import status

from exceptions.bases import LogicException


class BaseAuthException(LogicException):
    def __init__(self, http_status: int, message: str):
        super().__init__(
            http_status=http_status,
            message=message,
        )


class InvalidTokenError(BaseAuthException):
    def __init__(self):
        super().__init__(http_status=status.HTTP_403_FORBIDDEN, message="Invalid token")


class UserNotFound(BaseAuthException):
    def __init__(self):
        super().__init__(http_status=status.HTTP_400_BAD_REQUEST, message="User by this token not found")


class CredentialsException(BaseAuthException):
    def __init__(self, message: str):
        super().__init__(http_status=status.HTTP_401_UNAUTHORIZED, message=message)


class JWTDecodingError(LogicException):
    def __init__(self, message: str):
        super().__init__(http_status=status.HTTP_401_UNAUTHORIZED, message=message)
