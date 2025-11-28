from typing import ClassVar


class BaseHttpError(Exception):
    status_code: ClassVar[int]
    error_code: ClassVar[str]
    error: ClassVar[str]
