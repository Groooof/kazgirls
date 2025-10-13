from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import Integer, String

from models.bases import (
    BaseIdMixin,
    BaseSQLAlchemyModel,
    DateFieldsMixin,
)

if TYPE_CHECKING:
    from models.user import User


{
    "streamers:online": {
        "1": 1234567890,
        "2": 1234567890,
    },
    "streamers:1:viewers": {
        "1": 1234567890,
    },
    "streamers:1:data": {
        "is_busy": 1,
    },
}


class Streamer:
    user_id: int
    status: str  # online | offline


class Room(BaseIdMixin[Integer], DateFieldsMixin, BaseSQLAlchemyModel):
    __tablename__ = "rooms"
    __engine__ = "default"

    status: Mapped[str] = mapped_column(String(16))
    streamer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    viewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)

    streamer: Mapped["User"] = relationship()
    viewer: Mapped["User"] = relationship()

    def __str__(self) -> str:
        return self.id


class RoomMember(BaseIdMixin[Integer], DateFieldsMixin, BaseSQLAlchemyModel):
    __tablename__ = "rooms_members"
    __engine__ = "default"

    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    room: Mapped["Room"] = relationship()
    user: Mapped["User"] = relationship()

    def __str__(self) -> str:
        return f"room: {self.room_id} user: {self.user_id}"
