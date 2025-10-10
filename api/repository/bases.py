from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping
from typing import Any, Protocol, Self

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
