from datetime import UTC, datetime
from functools import partial
from typing import Any

from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from pydantic import BaseModel

from tests.custom_faker import fake


class BaseModelFactory[T: BaseModel](ModelFactory[T]):
    __is_base_factory__ = True
    __faker__ = fake


class BaseSQLAlchemyFactory[T](SQLAlchemyFactory[T]):
    __is_base_factory__ = True
    __faker__ = fake

    id = Use(fake.pyint, min_value=1, max_value=2**31 - 1)

    @classmethod
    def get_provider_map(cls) -> dict[type, Any]:
        providers_map = super().get_provider_map()

        custom_providers = {
            # Currency: lambda: DEFAULT_CURRENCY,
            # PhoneNumber: lambda: parse(cls.__faker__.ru_phone_number()),
            datetime: partial(cls.__faker__.date_time_between, tzinfo=UTC),
        }
        providers_map.update(custom_providers)
        return providers_map
