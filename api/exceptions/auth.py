from exceptions.bases import BaseHttpError


class WrongCredentials(BaseHttpError):
    status_code = 401
    error_code = "WRONG_CREDENTIALS"
    error = "Неверные данные авторизации"
