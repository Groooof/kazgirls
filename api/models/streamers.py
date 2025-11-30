from pathlib import Path
from typing import TYPE_CHECKING

from fastapi_storages import FileSystemStorage
from fastapi_storages.base import StorageImage
from fastapi_storages.integrations.sqlalchemy import ImageType
from sqlalchemy import ForeignKey, Integer, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.bases import BaseIdMixin, BaseSQLAlchemyModel, DateFieldsMixin
from settings.conf import settings

if TYPE_CHECKING:
    from models.user import User


avatars_storage = FileSystemStorage(path=settings.local_storage_path)


class StreamerProfile(BaseIdMixin[Integer], BaseSQLAlchemyModel):
    __tablename__ = "streamers_profiles"
    __engine__ = "default"

    name: Mapped[str] = mapped_column(String(255), nullable=True)
    force_rating: Mapped[float] = mapped_column(Numeric(3, 2), nullable=True)
    avatar: Mapped[StorageImage] = mapped_column(ImageType(storage=avatars_storage), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), unique=True)

    user: Mapped["User"] = relationship(back_populates="streamer_profile")

    @property
    def avatar_url(self) -> str | None:
        return self.avatar and str(Path("/media") / self.avatar.name) or None


class StreamerMark(BaseIdMixin[Integer], DateFieldsMixin, BaseSQLAlchemyModel):
    __tablename__ = "streamers_marks"
    __engine__ = "default"
    __table_args__ = (UniqueConstraint("streamer_id", "viewer_id"),)

    viewer_id: Mapped[int] = mapped_column(ForeignKey("viewers_profiles.id", ondelete="RESTRICT"))
    streamer_id: Mapped[int] = mapped_column(ForeignKey("streamers_profiles.id", ondelete="RESTRICT"))
    mark: Mapped[int] = mapped_column(SmallInteger)
