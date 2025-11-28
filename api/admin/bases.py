from collections.abc import Iterable
from datetime import datetime
from typing import Any, cast, no_type_check

import pytz
from fastapi import Request
from sqladmin import Admin, BaseView, ModelView
from sqladmin.authentication import AuthenticationBackend, login_required
from sqladmin.formatters import BASE_FORMATTERS
from sqladmin.helpers import get_column_python_type
from sqladmin.pagination import Pagination
from sqlalchemy import Select, func, inspect, or_, select
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import InstrumentedAttribute, Mapper, selectinload
from starlette.responses import RedirectResponse, Response

from dependencies.db import EngineTypeEnum, _get_db, engines
from exceptions.auth import WrongCredentials
from logic.auth import get_user_by_token, login_user_by_password, logout_user
from settings.conf import other_settings, settings


class CustomBaseView(BaseView):
    name = "Page"
    icon = "fa-solid fa-page"
    is_custom = True


class AdminBackend(AuthenticationBackend):
    def __init__(self, secret_key: str, engine: AsyncEngine):
        super().__init__(secret_key)
        self.engine = engine

    async def login(self, request: Request) -> bool | RedirectResponse:  # type: ignore
        form = await request.form()
        username, password = form["username"], form["password"]
        username = cast(str, username)
        password = cast(str, password)
        if not username or not password:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        try:
            async with _get_db() as db:
                token = await login_user_by_password(db, username, password)
                request.session.update({"token": token})
                return True
        except WrongCredentials:
            return False

    async def logout(self, request: Request) -> bool:
        token = request.session.get("token")
        if token:
            async with _get_db() as db:
                await logout_user(db, token)
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool | RedirectResponse:
        token = request.session.get("token")
        async with _get_db() as db:
            user = token and await get_user_by_token(db, token)

        if user and user.is_superuser:
            return True

        return RedirectResponse(request.url_for("admin:login"), status_code=302)


class BaseModelView(ModelView):
    _exclude: Iterable[InstrumentedAttribute[Any]] = []  # доп exclude кастомной логики
    can_edit = True
    can_create = True
    can_delete = True
    page_size = 100
    pagination_enable = True

    column_type_formatters = BASE_FORMATTERS | {
        float: lambda v: v and round(v, 2),
        datetime: lambda v: v
        and v.astimezone(pytz.timezone(other_settings.default_timezone)).strftime(other_settings.default_dt_format)
        or "",
    }

    @no_type_check
    def __init__(self):
        self.inspected_model: Mapper = inspect(self.model)
        # отображение стандартных полей по умолчанию, иначе нужно явно указывать
        self.column_list = self.column_list or (not self.column_exclude_list and self._get_model_fields())
        # TODO: Add autogenerate column labels
        super().__init__()

    @no_type_check
    def _get_model_fields(self):
        # кастомная логика, чтоб по дефолту отображать стандартные поля модели, но прятать ненужные
        # column_exclude_list возьмет все поля, кроме указанных, включая foreig_key, но выглядит часто не очень
        # поэтому возьмем свой __exclude, если не указан стандартный column_exclude_list
        # в самой библиотеке для отображения нельзя одновременно использовать column_list и column_exclude_list

        exclude = self._exclude and [exclude.key for exclude in self._exclude] or []
        return [getattr(self.model, attr) for attr in self.inspected_model.attrs.keys() if attr not in exclude]  # noqa: SIM118

    @no_type_check
    def search_query(self, stmt: Select, term: str) -> Select:
        """Specify the search query given the SQLAlchemy statement and term to search for.
        It can be used for doing more complex queries like JSON objects. For example:

        ```py
        return stmt.filter(MyModel.name == term)
        ```
        """
        is_search_correct_int = term.isdigit() and int(term).bit_length() <= 32
        expressions = []
        for attr in self._search_fields:
            search_column_type = get_column_python_type(attr)

            if isinstance(search_column_type, int) and is_search_correct_int:
                expression = attr == int(term)
            elif isinstance(search_column_type, str):
                expression = attr.ilike(f"%{term}%")
            else:
                continue
            expressions.append(expression)
        return stmt.filter(or_(*expressions))

    def is_accessible(self, request: Request) -> bool:
        return True

    def is_visible(self, request: Request) -> bool:
        return True

    async def list(self, request: Request) -> Pagination:
        if self.pagination_enable:
            return await super().list(request)

        search = request.query_params.get("search", None)
        stmt = self.list_query(request)

        for relation in self._list_relations:
            stmt = stmt.options(selectinload(relation))

        stmt = self.sort_query(stmt, request)

        if search:
            stmt = self.search_query(stmt=stmt, term=search)
            count = await self.count(request, select(func.count()).select_from(stmt))
        else:
            count = await self.count(request)

        rows = await self._run_query(stmt)

        return Pagination(
            rows=rows,
            page=1,
            page_size=self.page_size,
            count=count,
        )


class CustomAdmin(Admin):
    @login_required
    async def index(self, request: Request) -> Response:
        # Get stats from database
        users_count = 30

        context = {
            "request": request,
            "is_prod": settings.is_prod,
            "stats": {
                "users_count": users_count or 0,
                "today_date": datetime.now().strftime("%d %B %Y"),
                # Add more stats here
            },
        }
        return await self.templates.TemplateResponse(request, "admin/index.html", context)


authentication_backend = AdminBackend(secret_key=settings.secret_key, engine=engines[EngineTypeEnum.DEFAULT_ENGINE])
