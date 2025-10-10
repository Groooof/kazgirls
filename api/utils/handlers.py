from fastapi import status
from fastapi.responses import ORJSONResponse
from loguru import logger
from pydantic import ValidationError
from starlette.requests import Request

from exceptions.bases import BaseLogicException
from schemas.response import ErrorStruct
from settings.conf import settings


async def logic_exception_handler(request: Request, exc: BaseLogicException) -> ORJSONResponse:
    if settings.debug and settings.is_local:
        logger.exception("Logic exception: {}", exc.__repr__())
    else:
        logger.debug("Logic exception: {}", exc.__repr__())

    http_status = getattr(exc, "http_status", status.HTTP_400_BAD_REQUEST)
    response = ORJSONResponse(
        status_code=http_status,
        content=ErrorStruct.model_validate(exc).model_dump(),
    )
    return response


async def any_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
    logger.debug("Any exception: {}", exc.__repr__())

    http_status = getattr(exc, "status_code", None) or status.HTTP_500_INTERNAL_SERVER_ERROR
    message = getattr(exc, "detail", None) or "Internal error"
    response = ORJSONResponse(
        status_code=http_status,
        content=ErrorStruct(message=message).model_dump(),
    )
    return response


async def unhandled_validation_exception_handler(request: Request, exc: ValidationError) -> ORJSONResponse:
    """
    Для ситуаций, когда не обрабатываются автоматом
    """
    logger.debug("Unhandled validation exception: {}", exc)
    logger.debug("Unhandled validation exception: {}", exc.__dict__)
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY

    msg = getattr(exc, "message", None) or "Validation error"
    response = ORJSONResponse(
        status_code=http_status,
        content=ErrorStruct(message=msg, details={"errors": exc.errors()}).model_dump(),
    )
    return response
