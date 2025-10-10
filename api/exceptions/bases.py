import dataclasses
from http import HTTPStatus as status

type HTTPStatus = int


@dataclasses.dataclass
class DetailsStruct:
    human_message: str | None = None
    system_message: str | None = None


class BaseLogicException(Exception):
    details = None
    http_status: HTTPStatus

    def __init__(
        self,
        message: str,
        http_status: HTTPStatus = status.BAD_REQUEST,
        details: DetailsStruct | None = None,
    ):
        self.http_status = http_status
        self.message = message

        if details:
            self.details = dataclasses.asdict(details)

    def __str__(self):
        cause = self.__cause__ and self.__cause__.__class__ or ""
        return f"{self.message} {cause}"


class LogicException(BaseLogicException):
    """
    Исключение, которое можно показывать пользователю
    """

    documentation_url: str | None = None

    def __init__(
        self,
        message: str,
        http_status: HTTPStatus = status.BAD_REQUEST,
        details: DetailsStruct | None = None,
        documentation_url: str | None = None,
    ):
        super().__init__(message=message, http_status=http_status, details=details)
        if documentation_url:
            self.documentation_url = documentation_url


class PrivateLogicException(BaseLogicException):
    """
    Исключение, которое скрывает message и details от пользователя информацию показывать пользователю
    """

    def __init__(
        self,
        message: str,
        http_status: HTTPStatus = status.BAD_REQUEST,
        details: DetailsStruct | None = None,
    ):
        super().__init__(message=message, http_status=http_status, details=details)
