from fastapi import APIRouter

from .auth import router as token_router
from .messages import router as messages_router
from .streamers import router as streamers_router
from .viewers import router as viewers_router

router = APIRouter()

router.include_router(token_router, prefix="/tokens")
router.include_router(streamers_router, prefix="/streamers")
router.include_router(viewers_router, prefix="/viewers")
router.include_router(messages_router, prefix="/messages")
