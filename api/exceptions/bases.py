from typing import ClassVar


class BaseHttpError(Exception):
    status_code: ClassVar[int]
    error_code: ClassVar[str]
    error: ClassVar[str]


class Http403(BaseHttpError):
    status_code = 403
    error_code = "FORBIDDEN"
    error = "Доступ запрещен"


class Http404(BaseHttpError):
    status_code = 404
    error_code = "NOT_FOUND"
    error = "Объект не найден"


class Http422(BaseHttpError):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    error = "Неверный формат запроса"


class Http500(BaseHttpError):
    status_code = 500
    error_code = "INTERNAL_ERROR"
    error = "Неизвестная ошибка"
