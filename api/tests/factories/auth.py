from typing import Any

from polyfactory.fields import Use
from uuid_extensions import uuid7str

from models.user import User, UserSession
from schemas.auth import TokenTypesChoices
from tests.factories.bases import BaseSQLAlchemyFactory
from utils.auth import get_password_hash


class UserFactory(BaseSQLAlchemyFactory[User]):
    is_superuser = False
    is_active = True

    @classmethod
    def build(cls, *_: Any, **kwargs: Any) -> User:
        instance = super().build(**kwargs)
        instance.password = get_password_hash(instance.password)
        return instance


class UserSessionFactory(BaseSQLAlchemyFactory[UserSession]):
    session = Use(uuid7str)
    token_type = TokenTypesChoices.session
    is_active = True
