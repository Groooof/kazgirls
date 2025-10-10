from typing import Any

from fastapi import status

from schemas.response import ErrorStruct

type _Responses = dict[int | str, dict[str, Any]]


class Responses:
    """
    Синтаксический сахар, для описания возможных ответов в endpoint
    Формирует валидный словарь для параметра responses.
    responses добавленные при инициализации router применяются для всех endpoint в этом router
    responses добавленные в endpoint, применяются только к нему + глобальные
    конкретные response внутри endpoint подменят description описанный здесь при получении этого response,
    но в документации отображется description добавленый в router
    """

    response_codes = {
        status.HTTP_401_UNAUTHORIZED: ErrorStruct(message="Not authorized").model_dump(by_alias=True),
        status.HTTP_403_FORBIDDEN: ErrorStruct(message="Access forbidden").model_dump(by_alias=True),
        status.HTTP_404_NOT_FOUND: ErrorStruct(message="Object not found").model_dump(by_alias=True),
        status.HTTP_409_CONFLICT: ErrorStruct(message="Conflict").model_dump(by_alias=True),
        status.HTTP_422_UNPROCESSABLE_ENTITY: ErrorStruct(message="Unprocessable entity").model_dump(by_alias=True),
    }

    def __call__(self, *args: int, **kwargs) -> _Responses:
        data: _Responses = {}
        for arg in args:
            data[arg] = self.response_codes[arg]
        return data


responses = Responses()
