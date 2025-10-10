from fastapi import Request
from sqladmin import expose
from sqladmin.authentication import login_required
from sqladmin.templating import _TemplateResponse

from admin.bases import CustomBaseView


class ConstanceView(CustomBaseView):
    name = "Settings"
    icon = "fa-solid fa-gear"

    @expose("/constance", methods=["GET"])
    @login_required
    async def custom_page(self, request: Request) -> _TemplateResponse:
        context = {"request": request, "my_var": 123, "constances": {}}

        return await self.templates.TemplateResponse(request, "admin/constance.html", context=context)
