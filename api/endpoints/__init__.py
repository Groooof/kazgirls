from fastapi import APIRouter

from settings.conf import settings

from ._tags import Tags
from .auth import router as token_router

external_api_router = APIRouter()
internal_api_router = APIRouter(include_in_schema=True)


external_api_router.include_router(token_router, prefix="/tokens", include_in_schema=False)

internal_api_router.include_router(token_router, prefix="/tokens")
