import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any

import socketio

from . import lobby, streamers


class registrator:
    def __init__(self, sio: socketio.AsyncServer) -> None:
        self.sio = sio
        self.namespace = None

    def __call__(self, func: Callable[..., Any], event: str | None = None) -> None:
        def decorator(func: Callable[..., Any]):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if "sio" in inspect.signature(func).parameters:
                    kwargs["sio"] = self.sio
                return await func(*args, **kwargs)

            return wrapper

        event = event or func.__name__
        self.sio.on(event, self.namespace, decorator(func))


def register_handlers(sio: socketio.AsyncServer) -> None:
    register = registrator(sio)
    register.namespace = streamers.namespace

    register(streamers.connect)
    register(streamers.disconnect)
    register(streamers.ping)
    register(streamers.webrtc_offer, "webrtc:offer")
    register(streamers.webrtc_answer, "webrtc:answer")
    register(streamers.webrtc_ice, "webrtc:ice")

    register.namespace = lobby.namespace
    register(lobby.connect)
    register(lobby.disconnect)
