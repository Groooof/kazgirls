from fastapi import APIRouter

from settings.conf import settings

from ._tags import Tags
from .auth import router as token_router

router = APIRouter()

router.include_router(token_router, prefix="/tokens")
