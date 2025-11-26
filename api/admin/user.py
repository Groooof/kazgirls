from fastapi import Request

from admin.bases import BaseModelView
from dependencies.db import _get_db
from models.streamers import StreamerProfile
from models.user import User
from repository.streamers import StreamerProfileRepository
from utils.auth import get_password_hash


class UserAdmin(BaseModelView, model=User):
    _exclude = [User.sessions, User.password]
    column_details_exclude_list = [User.sessions]
    form_excluded_columns = column_details_exclude_list
    column_searchable_list = [User.username]
    export_types = []

    form_create_rules = [
        User.username.key,
        User.password.key,
        User.name.key,
        User.is_streamer.key,
        User.is_superuser.key,
    ]
    form_edit_rules = [
        User.username.key,
        User.name.key,
        User.is_streamer.key,
        User.is_superuser.key,
        User.is_active.key,
    ]

    async def on_model_change(self, data: dict, model: User, is_created: bool, request: Request) -> None:  # noqa FBT001
        if is_created:
            data["password"] = get_password_hash(data["password"])

        if not is_created and data["is_streamer"] and not model.is_streamer:
            async with _get_db() as db:
                repo = StreamerProfileRepository(db)
                is_exists = await repo.exists(StreamerProfile.user_id == model.id)
                if not is_exists:
                    await repo.save(StreamerProfile(user_id=model.id))

        await super().on_model_change(data, model, is_created, request)

    async def after_model_change(self, data: dict, model: User, is_created: bool, request: Request) -> None:
        if is_created and data["is_streamer"]:
            async with _get_db() as db:
                repo = StreamerProfileRepository(db)
                await repo.save(StreamerProfile(user_id=model.id))

        await super().after_model_change(data, model, is_created, request)
