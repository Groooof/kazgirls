from markupsafe import Markup

from admin.bases import BaseModelView
from models.streamers import StreamerMark, StreamerProfile


class StreamerProfileAdmin(BaseModelView, model=StreamerProfile):
    column_formatters = {
        "avatar": lambda m, a: Markup(
            '<img src="{}" style="max-height: 100px; max-width: 100px; object-fit: cover;">'
        ).format(m.avatar_url),
    }
    column_formatters_detail = column_formatters

    def on_model_change(self, data, model, is_created, request):
        if not is_created and model.user_id != int(data["user"]):
            raise Exception("Нельзя менять привязку к пользователю!")
        return super().on_model_change(data, model, is_created, request)


class StreamerMarksAdmin(BaseModelView, model=StreamerMark):
    pass
