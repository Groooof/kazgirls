from admin.bases import BaseModelView
from models.viewers import ViewerProfile


class ViewerProfileAdmin(BaseModelView, model=ViewerProfile):
    def on_model_change(self, data, model, is_created, request):
        if not is_created and model.user_id != int(data["user"]):
            raise Exception("Нельзя менять привязку к пользователю!")
        return super().on_model_change(data, model, is_created, request)
