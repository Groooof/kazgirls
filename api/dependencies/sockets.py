import socketio

from settings.conf import databases

server = socketio.AsyncServer(
    async_mode="asgi",
    client_manager=socketio.AsyncRedisManager(str(databases.sockets_redis_url)),
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
    transports=["websocket"],
)
