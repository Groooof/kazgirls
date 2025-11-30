from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.bases import BaseIdMixin, BaseSQLAlchemyModel

if TYPE_CHECKING:
    from models.user import User


class ViewerProfile(BaseIdMixin[Integer], BaseSQLAlchemyModel):
    __tablename__ = "viewers_profiles"
    __engine__ = "default"

    name: Mapped[str] = mapped_column(String(255), nullable=True)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), unique=True)

    user: Mapped["User"] = relationship(back_populates="viewer_profile")
