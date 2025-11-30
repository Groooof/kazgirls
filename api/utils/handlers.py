from fastapi.responses import ORJSONResponse
from pydantic import ValidationError
from starlette.requests import Request

from exceptions.bases import BaseHttpError, Http422, Http500


async def logic_exception_handler(request: Request, exc: BaseHttpError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "error_code": exc.error_code},
    )


async def any_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
    return await logic_exception_handler(request, Http500())


async def unhandled_validation_exception_handler(request: Request, exc: ValidationError) -> ORJSONResponse:
    return await logic_exception_handler(request, Http422())
