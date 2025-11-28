from fastapi.responses import ORJSONResponse
from loguru import logger
from pydantic import ValidationError
from starlette.requests import Request

from exceptions.bases import BaseHttpError


async def logic_exception_handler(request: Request, exc: BaseHttpError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "error_code": exc.error_code},
    )


async def any_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=500,
        content={"error": "Неизвестная ошибка", "error_code": "INTERNAL_ERROR"},
    )


async def unhandled_validation_exception_handler(request: Request, exc: ValidationError) -> ORJSONResponse:
    logger.warning(100 * "A")
    return ORJSONResponse(
        status_code=422,
        content={"error": "Ошибка валидации", "error_code": "VALIDATION_ERROR"},
    )
