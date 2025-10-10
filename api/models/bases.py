import typing
import uuid
from collections.abc import Iterable
from datetime import datetime, time

import phonenumbers
from phonenumbers import PhoneNumber, PhoneNumberFormat
from sqlalchemy import (
    ARRAY,
    JSON,
    UUID,
    DateTime,
    Sequence,
    SmallInteger,
    String,
    Time,
    TypeDecorator,
    Unicode,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
)
from sqlalchemy.sql import operators
from sqlalchemy.types import Integer
from sqlalchemy_utils.types.scalar_coercible import ScalarCoercible

from utils.libs import utc_now

# Models
JSONVariant = MutableDict.as_mutable(JSON().with_variant(JSONB(none_as_null=True), "postgresql"))
UUIDVariant = String().with_variant(UUID, "postgresql")
ARRAYSmallVariant = MutableDict.as_mutable(JSON().with_variant(ARRAY(SmallInteger()), "postgresql"))
SEQUENCE_START = 1


class Seq(Sequence):
    pass


class BaseSQLAlchemyModel(DeclarativeBase):
    __abstract__ = True

    type_annotation_map = {
        datetime: DateTime(timezone=True),
        time: Time(timezone=True),
        dict: JSONVariant,
        uuid.UUID: UUIDVariant,
    }

    def as_dict(self) -> dict:
        obj_copy = self.__dict__.copy()
        obj_copy.pop("_sa_instance_state", None)
        return obj_copy

    def clone(self, exclude: Iterable[str] | None = None):
        exclude = exclude or []
        # Создаем новый экземпляр класса без первичного ключа
        return self.__class__(
            **{
                column.name: getattr(self, column.name)
                for column in self.__table__.columns
                if column.name != "id" and column.name not in exclude
            },
        )

    def __repr__(self):
        return f"<{self.__class__.__name__}, ID: {self.id}>"


class DateFieldsMixin:
    created: Mapped[datetime] = mapped_column(default=utc_now)
    updated: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)


class BaseIdMixin[T: Integer]:
    _id_type: type[T]

    def __init_subclass__(cls, **kwargs):
        """Инициализация подкласса. Берет тип из дженерика"""
        types = typing.get_args(cls.__orig_bases__[0])  # noqa: F821
        cls._id_type = types[0] if types else Integer
        super().__init_subclass__(**kwargs)

    @declared_attr
    def id(cls) -> Mapped[int]:
        """
        todo: можно расширить и до uuid, но надо как-то динамически менять тип результата
        (скорее всего в  __init_subclass__)
        """
        table_name = cls.__tablename__
        sequence = Seq(f"{table_name}_id_seq", start=SEQUENCE_START, data_type=cls._id_type)
        column = mapped_column(cls._id_type, sequence, primary_key=True)
        return column


class PhoneNumberSQLAlchemyType(ScalarCoercible, TypeDecorator):
    STORE_FORMAT = PhoneNumberFormat.E164
    impl = Unicode(20)
    python_type = PhoneNumber
    cache_ok = True

    def __init__(self, region=None, max_length=20, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.region = region
        self.impl = Unicode(max_length)

    def coerce_compared_value(self, op, value):
        if op in (operators.contains_op,):
            return String()
        return self

    def process_bind_param(self, value: str | PhoneNumber | None, dialect):
        if not value:
            return value
        if not isinstance(value, PhoneNumber):
            value = phonenumbers.parse(value, region=self.region)
        return phonenumbers.format_number(value, self.STORE_FORMAT)

    def process_result_value(self, value, dialect):
        if value:
            return phonenumbers.parse(value, region=self.region)
        return value

    def _coerce(self, value):
        if value and not isinstance(value, PhoneNumber):
            phonenumbers.parse(value, region=self.region)

        return value or None
