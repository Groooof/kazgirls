from typing import Any

from models.user import User
from tests.factories.bases import BaseSQLAlchemyFactory
from utils.auth import get_password_hash


class UserFactory(BaseSQLAlchemyFactory[User]):
    is_superuser = False
    is_active = True
    is_streamer = False

    @classmethod
    def build(cls, *_: Any, **kwargs: Any) -> User:
        instance = super().build(**kwargs)
        instance.password = get_password_hash(instance.password)
        return instance
