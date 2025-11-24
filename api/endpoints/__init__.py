from fastapi import APIRouter

from settings.conf import settings

from ._tags import Tags
from .auth import router as token_router
from .lobby import router as lobby_router

router = APIRouter()

router.include_router(token_router, prefix="/tokens")
router.include_router(lobby_router, prefix="/lobby")
