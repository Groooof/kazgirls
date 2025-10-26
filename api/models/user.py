from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import BigInteger, Integer

from models.bases import BaseIdMixin, BaseSQLAlchemyModel, DateFieldsMixin


class User(BaseIdMixin[Integer], DateFieldsMixin, BaseSQLAlchemyModel):
    __tablename__ = "users"
    __engine__ = "default"

    username: Mapped[str]
    password: Mapped[str]
    name: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)
    is_streamer: Mapped[bool] = mapped_column(default=False)
    is_superuser: Mapped[bool] = mapped_column(default=False)

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")

    def __str__(self) -> str:
        return self.username


class UserSession(BaseIdMixin[BigInteger], DateFieldsMixin, BaseSQLAlchemyModel):
    __tablename__ = "user_sessions"
    __engine__ = "default"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str]
    expired: Mapped[datetime] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)

    user: Mapped["User"] = relationship()

    def __str__(self) -> str:
        return f"session: {self.id} user: {self.user_id}"
