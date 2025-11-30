import typing
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import AsyncIterator, Iterable, Mapping, MutableMapping
from typing import Any, Literal, Protocol, Self, cast

import sqlalchemy.exc
from sqlalchemy import Column, ColumnElement, Result, Select, delete, desc, select, true, update
from sqlalchemy.engine.result import ScalarResult
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import joinedload, load_only

from models.bases import BaseSQLAlchemyModel

from .dto import UNSET, UnsetType
from .types import AuthTypes, CookieTypes, HeaderTypes, QueryParamTypes, RequestFiles, TimeoutTypes


class BaseRepositoryAbstract(ABC):
    @abstractmethod
    async def get(self, *args, **kwargs): ...

    @abstractmethod
    async def add(self, *args, **kwargs): ...

    @abstractmethod
    async def update(self, *args, **kwargs): ...

    @abstractmethod
    async def delete(self, *args, **kwargs): ...

    @abstractmethod
    async def first(self, *args, **kwargs): ...


class ResponseProtocol(Protocol):
    """
    Протокол для унификации HTTP ответов разных библиотек
    TODO: Расширить для stream, т.к. контент не можеть быть пропсом
    """

    @property
    def status_code(self) -> int:
        """HTTP статус код ответа"""
        ...

    @property
    def headers(self) -> MutableMapping[str, str]:
        """HTTP заголовки ответа"""
        ...

    @property
    def content(self) -> bytes:
        """Содержимое ответа в виде bytes"""
        ...

    @property
    def text(self) -> str:
        """Содержимое ответа в виде строки"""
        ...

    def json(self) -> Any:
        """Десериализованный JSON ответ"""
        ...

    def raise_for_status(self) -> Self:
        """Проверить статус ответа и вызвать исключение при ошибке"""
        ...

    @property
    def is_success(self) -> bool:
        """Проверка успешности запроса (2xx статус)"""
        ...


class BaseExternalSourceRequestRepository(ABC):
    @abstractmethod
    async def get(
        self,
        url: str,
        query_params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UnsetType = UNSET,
        follow_redirects: bool | UnsetType = UNSET,
        timeout: TimeoutTypes | UnsetType = UNSET,
        *,
        raise_for_status: bool = False,
    ) -> ResponseProtocol: ...

    @abstractmethod
    async def put(
        self,
        url: str,
        data: Mapping[str, Any] | None = None,
        files: RequestFiles | None = None,
        json: Any | None = None,
        query_params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UnsetType = UNSET,
        follow_redirects: bool | UnsetType = UNSET,
        timeout: TimeoutTypes | UnsetType = UNSET,
        *,
        raise_for_status: bool = False,
    ) -> ResponseProtocol: ...

    @abstractmethod
    async def post(
        self,
        url: str,
        data: Mapping[str, Any] | None = None,
        files: RequestFiles | None = None,
        json: Any | None = None,
        query_params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UnsetType = UNSET,
        follow_redirects: bool | UnsetType = UNSET,
        timeout: TimeoutTypes | UnsetType = UNSET,
        *,
        raise_for_status: bool = False,
    ) -> ResponseProtocol: ...

    @abstractmethod
    async def patch(
        self,
        url: str,
        data: Mapping[str, Any] | None = None,
        files: RequestFiles | None = None,
        json: Any | None = None,
        query_params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UnsetType = UNSET,
        follow_redirects: bool | UnsetType = UNSET,
        timeout: TimeoutTypes | UnsetType = UNSET,
        *,
        raise_for_status: bool = False,
    ) -> ResponseProtocol: ...

    @abstractmethod
    async def delete(
        self,
        url: str,
        query_params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UnsetType = UNSET,
        follow_redirects: bool | UnsetType = UNSET,
        timeout: TimeoutTypes | UnsetType = UNSET,
        *,
        raise_for_status: bool = False,
    ) -> ResponseProtocol: ...


class BaseSQLRepository[T: BaseSQLAlchemyModel](BaseRepositoryAbstract):
    """
    Базовый класс для управления моделями
    """

    model: type[T]
    db: AsyncSession

    def __init_subclass__(cls, **kwargs):
        """
        Инициализация подкласса. Берет модель из дженерика
        """
        super().__init_subclass__(**kwargs)
        [cls.model] = typing.get_args(cls.__orig_bases__[0])

    def __init__(self, db: AsyncSession):
        self.db: AsyncSession = db

    async def delete(self, obj):
        await self.db.delete(obj)
        return obj

    async def delete_objects(self, objects: Iterable[T]):
        for obj in objects:
            await self.delete(obj)
        await self.db.flush()

    async def delete_all(self, *args, **kwargs) -> int:
        statement = delete(self.model).where(*args).filter_by(**kwargs)
        result = await self.exec(statement)
        return result.rowcount

    async def exec(self, statement) -> Result:
        result = await self.db.execute(statement)
        return result

    async def _exec_scalar(self, statement) -> ScalarResult:
        result = await self.exec(statement)
        return result.scalars()

    def _select_query_builder(  # noqa: C901
        self,
        *args,
        select_related: Iterable | None = None,
        join: Iterable | None = None,
        options: Iterable | None = None,
        only: Iterable | None = None,
        selected_columns: Iterable | None = None,
        order_by: list[ColumnElement | str] | ColumnElement | str | None = None,
        limit: int | tuple[int, int] | None = None,
        **kwargs,
    ) -> Select:
        query = select(*selected_columns) if selected_columns else select(self.model)
        if args:
            query = query.where(*args)
        if kwargs:
            query = query.filter_by(**kwargs)
        if join:
            # todo: принимать в join Iterable[tuple[model, tuple[onclause column]]]
            for table in join:
                query = query.join(table)
        if options:
            query = query.options(*options)
        if select_related:
            sr = [joinedload(field) for field in select_related]
            query = query.options(*sr)
        if only is not None:
            query = query.options(load_only(*only))
        has_order = order_by is not None

        if has_order and isinstance(order_by, list):
            query = query.order_by(*order_by)
        elif has_order:
            query = query.order_by(order_by)

        has_limit = limit is not None
        if has_limit and isinstance(limit, int):
            query = query.limit(limit)
        elif has_limit:
            query = query.offset(limit[0]).limit(limit[1])
        return query

    async def iterator(
        self,
        *args,
        chunk_size: int = 2000,
        select_related: Iterable | None = None,
        join: list | None = None,
        order_by: list[ColumnElement | str] | ColumnElement | str | None = None,
        limit: int | tuple[int, int] | None = None,
        only: Iterable | None = None,
        **kwargs,
    ) -> AsyncIterator[T]:
        query = self._select_query_builder(
            *args, select_related=select_related, join=join, order_by=order_by, limit=limit, only=only, **kwargs
        )
        return await self.db.stream_scalars(query.execution_options(yield_per=chunk_size))

    async def rollback(self):
        await self.db.rollback()

    async def get(
        self,
        *args,
        raise_exception_if_none: bool = True,
        select_related: Iterable | None = None,
        order_by: list[ColumnElement | str] | ColumnElement | str | None = None,
        join: Iterable | None = None,
        unique: bool = False,
        **kwargs,
    ) -> T | None:
        result = await self._filter(
            *args,
            select_related=select_related,
            join=join,
            limit=2,
            order_by=order_by,
            **kwargs,
        )
        if unique:
            result = result.unique()
        try:
            return result.one()
        except sqlalchemy.exc.NoResultFound:
            if raise_exception_if_none:
                raise
        return None

    def _base_order_by_query_builder(
        self,
        *args,
        column=None,
        ordering: Literal["asc", "desc"] = "asc",
        limit: int | None = None,
        select_related: Iterable | None = None,
        join: Iterable | None = None,
        options: Iterable | None = None,
        **kwargs,
    ):
        sort_column = column or self.model.id
        if not sort_column:
            raise ValueError("Column for sorting didn't specify")
        order_by_condition = desc(sort_column) if ordering == "desc" else sort_column
        statement = self._select_query_builder(
            *args,
            select_related=select_related,
            join=join,
            order_by=order_by_condition,
            limit=limit,
            options=options,
            **kwargs,
        )
        return statement

    async def first(
        self,
        *args,
        column=None,
        options: Iterable | None = None,
        select_related: Iterable | None = None,
        join: Iterable | None = None,
        **kwargs: Any,
    ) -> T | None:
        statement = self._base_order_by_query_builder(
            *args, column=column, limit=1, select_related=select_related, join=join, options=options, **kwargs
        )
        result = await self._exec_scalar(statement)
        return result.first()

    async def exists(self, *args, join: Iterable | None = None) -> bool:
        """Без kwargs, т.к. нет явного FROM"""

        statement = self._select_query_builder(*args, join=join, selected_columns=[true()])
        result = await self.exec(statement)
        return bool(result.scalar())

    async def last(
        self,
        *args,
        column=None,
        select_related: Iterable | None = None,
        join: Iterable | None = None,
        **kwargs,
    ) -> T | None:
        statement = self._base_order_by_query_builder(
            *args, column=column, ordering="desc", limit=1, select_related=select_related, join=join, **kwargs
        )
        result = await self._exec_scalar(statement)
        return result.first()

    async def list_(
        self,
        *args,
        select_related: Iterable | None = None,
        join: Iterable | None = None,
        unique: bool = False,
        order_by: list[ColumnElement | str] | ColumnElement | str | None = None,
        limit: int | tuple[int, int] | None = None,
        **kwargs,
    ) -> list[T]:
        result = await self._filter(
            *args,
            select_related=select_related,
            join=join,
            order_by=order_by,
            limit=limit,
            **kwargs,
        )
        if unique:
            result = result.unique()
        return cast(list[T], result.all())

    def add(self, obj: T) -> None:
        self.db.add(obj)

    async def save(self, obj: T) -> None:
        self.add(obj)
        await self.flush()

    async def add_all(
        self,
        instances: Iterable[T],
        *,
        batch_size: int | None = None,
    ):
        if batch_size is None:
            self.db.add_all(instances)
            await self.flush()
            return

        if batch_size < 1:
            raise ValueError("batch_size must be greater than 0")
        instances = tuple(i for i in instances)
        max_size = max(len(instances), 1)
        size = min(batch_size, max_size)
        for i in range(0, len(instances), size):
            self.db.add_all(instances[i : i + size])
            await self.flush()

    async def refresh(self, obj: T) -> None:
        await self.db.refresh(obj)

    async def flush(self):
        await self.db.flush()

    async def get_or_create(self, defaults: dict | None = None, **kwargs) -> tuple[T, bool]:
        instance = await self.get(**kwargs, raise_exception_if_none=False)
        if instance:
            return instance, False
        else:
            kwargs |= defaults or {}
            instance = self.model(**kwargs)
            self.add(instance)
            return instance, True

    async def _filter(
        self,
        *args,
        select_related: Iterable | None = None,
        join: Iterable | None = None,
        order_by: list[ColumnElement | str] | ColumnElement | str | None = None,
        limit: int | tuple[int, int] | None = None,
        select_for_update: bool = False,
        **kwargs,
    ) -> ScalarResult:
        query = self._select_query_builder(
            *args,
            select_related=select_related,
            join=join,
            order_by=order_by,
            limit=limit,
            **kwargs,
        )
        if select_for_update:
            query = query.with_for_update()
        return await self._exec_scalar(query)

    async def update(self, *args, values: dict, commit=True, **kwargs):
        query = update(self.model)
        if args:
            query = query.where(*args)
        if kwargs:
            query = query.filter_by(**kwargs)
        await self.db.execute(query.values(**values))
        if commit:
            await self.db.flush()

    async def update_or_create(self, defaults: dict | None = None, commit: bool = True, **kwargs):
        get_query = self._select_query_builder(**kwargs).with_for_update()
        result = (await self._exec_scalar(get_query)).one_or_none()

        defaults = defaults or {}
        created = False

        if result:
            for k, v in defaults.items():
                setattr(result, k, v)
        else:
            created = True
            kwargs |= defaults
            result = self.model(**kwargs)

        self.add(result)
        if commit:
            await self.flush()
        return result, created

    async def in_bulk_many[C: BaseSQLAlchemyModel](
        self, query: Select, field: str | Column, *, custom_type: type[C] | None = None
    ) -> dict[Any, list[T | C]]:
        result = await self.exec(query)
        mapped_rows = result.mappings().all()
        result = defaultdict(list)
        field_name = field.name if isinstance(field, Column) else field
        result_type = custom_type if custom_type is not None else self.model
        for row in mapped_rows:
            lookup_field_value = row[field_name]
            result[lookup_field_value].append(row[result_type.__name__])
        return result

    async def get_object_name(self, obj) -> str:
        if not self.model:
            raise AttributeError("Method not available for object without model.")
        return f"{self.model.__name__}: {obj.id}"

    @classmethod
    def get_fields(cls) -> set[str]:
        return {c.name for c in cls.model.__table__.columns}
