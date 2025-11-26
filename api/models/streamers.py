from typing import TYPE_CHECKING

from fastapi_storages import FileSystemStorage
from fastapi_storages.integrations.sqlalchemy import FileType
from sqlalchemy import Float, ForeignKey, Integer, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.bases import BaseIdMixin, BaseSQLAlchemyModel, DateFieldsMixin
from settings.conf import settings

if TYPE_CHECKING:
    from models.user import User


class StreamerProfile(BaseIdMixin[Integer], BaseSQLAlchemyModel):
    __tablename__ = "streamers_profiles"
    __engine__ = "default"

    avatar = mapped_column(FileType(storage=FileSystemStorage(path=settings.local_storage_path)), nullable=True)
    force_rating: Mapped[float] = mapped_column(Float(2), nullable=True)
    force_rating_votes: Mapped[int] = mapped_column(Integer, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), unique=True)

    user: Mapped["User"] = relationship(back_populates="streamer_profile")


class StreamerMark(BaseIdMixin[Integer], DateFieldsMixin, BaseSQLAlchemyModel):
    __tablename__ = "streamers_marks"
    __engine__ = "default"
    __table_args__ = (UniqueConstraint("streamer_id", "user_id"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    streamer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    mark: Mapped[int] = mapped_column(SmallInteger)
