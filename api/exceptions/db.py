from http import HTTPStatus as status

from .bases import BaseLogicException


class DoesNotExist(BaseLogicException):
    def __init__(self, model: type):
        super().__init__(
            http_status=status.NOT_FOUND,
            message=f"{model.__name__} does not exist",
        )


class ObjectNotFound(BaseLogicException):
    def __init__(self, model: type):
        super().__init__(
            http_status=status.NOT_FOUND,
            message=f"{model.__name__} not found",
        )


class MultipleObjectsReturned(BaseLogicException):
    def __init__(self, model: type):
        super().__init__(
            http_status=status.CONFLICT,
            message=f"Multiple objects returned for {model.__name__}, expected one",
        )
