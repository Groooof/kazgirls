import socketio
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio.session import AsyncSession

from models.messages import Message
from repository.messages import MessageRepository
from schemas.messages import MessageSchema
from settings.conf import sockets_namespaces


async def create_message(
    sio: socketio.AsyncServer, db: AsyncSession, redis: Redis, streamer_id: int, from_streamer: bool, text: str
) -> None:
    viewer_id = await redis.hget("streamers:viewers", streamer_id)
    if not viewer_id:
        logger.critical("Not found viewer id when seding message (streamer id: {})", streamer_id)
        return

    repo = MessageRepository(db)
    obj = Message(streamer_id=streamer_id, viewer_id=viewer_id, from_streamer=from_streamer, text=text)
    await repo.save(obj)

    if from_streamer:
        sid = await redis.hget("viewers:sid", viewer_id)
    else:
        sid = await redis.hget("streamers:sid", streamer_id)

    data = MessageSchema(created=obj.created, text=text, from_streamer=from_streamer)
    await sio.emit("message", data.model_dump(), to=sid, namespace=sockets_namespaces.streamers)


def _get_message_schema_from_obj(message: Message) -> MessageSchema:
    return MessageSchema(from_streamer=message.from_streamer, text=message.text, created=message.created)


async def get_messages(db: AsyncSession, streamer_id: int, viewer_id: int) -> list[MessageSchema]:
    repo = MessageRepository(db)
    messages = await repo.list_(Message.viewer_id == viewer_id, Message.streamer_id == streamer_id)
    return [_get_message_schema_from_obj(message) for message in messages]
