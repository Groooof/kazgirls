from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.bases import BaseIdMixin, BaseSQLAlchemyModel, DateFieldsMixin

if TYPE_CHECKING:
    pass


class Message(BaseIdMixin[BigInteger], DateFieldsMixin, BaseSQLAlchemyModel):
    __tablename__ = "messages"
    __engine__ = "default"

    streamer_id: Mapped[int] = mapped_column(ForeignKey("streamers_profiles.id", ondelete="RESTRICT"))
    viewer_id: Mapped[int] = mapped_column(ForeignKey("viewers_profiles.id", ondelete="RESTRICT"))
    from_streamer: Mapped[bool] = mapped_column(Boolean)
    text: Mapped[str] = mapped_column(Text)
