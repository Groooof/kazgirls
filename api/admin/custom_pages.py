from datetime import datetime

from fastapi import Request
from sqladmin import expose
from sqladmin.authentication import login_required
from sqladmin.templating import _TemplateResponse

from admin.bases import CustomBaseView
from dependencies.db import _get_db
from dependencies.redis import _get_redis
from repository.streamers import StreamerProfileRepository
from repository.viewers import ViewerProfileRepository


class ConstanceView(CustomBaseView):
    name = "Settings"
    icon = "fa-solid fa-gear"

    @expose("/constance", methods=["GET"])
    @login_required
    async def custom_page(self, request: Request) -> _TemplateResponse:
        context = {"request": request, "my_var": 123, "constances": {}}

        return await self.templates.TemplateResponse(request, "admin/constance.html", context=context)


class StreamersOnlineView(CustomBaseView):
    name = "Онлайн стримеры"
    icon = "fa-solid fa-tower-broadcast"  # любая иконка FontAwesome

    @expose("/streamers-data", methods=["GET"])
    async def streamers_data(self, request: Request):
        async with _get_db() as db, _get_redis() as redis:
            streamers_repo = StreamerProfileRepository(db)
            viewers_repo = ViewerProfileRepository(db)

            viewers = await viewers_repo.list_()
            viewers_by_id = {viewer.id: viewer for viewer in viewers}
            streamers = await streamers_repo.list_()
            streamers_online = dict(await redis.zrange("streamers:online", 0, -1, withscores=True))
            viewers_online = dict(await redis.zrange("viewers:online", 0, -1, withscores=True))
            streamers_viewers = await redis.hgetall("streamers:viewers")
            streamers_sid = await redis.hgetall("streamers:sid")
            viewers_sid = await redis.hgetall("viewers:sid")

        rows = []
        for streamer_obj in streamers:
            streamer_id = str(streamer_obj.id)

            streamer = f"{streamer_obj.name} (id: {streamer_obj.id})"
            streamer_last_seen = streamers_online.get(streamer_id)
            streamer_last_seen = streamer_last_seen and datetime.fromtimestamp(streamer_last_seen)
            streamer_sid = streamers_sid.get(streamer_id)

            viewer_id = streamers_viewers.get(streamer_id)

            viewer_obj = viewers_by_id.get(viewer_id)
            viewer = viewer_obj and f"{viewer_obj and viewer_obj.name or 'unknown'} (id: {viewer_obj.id})"
            viewer_last_seen = viewers_online.get(viewer_id)
            streamer_last_seen = viewer_last_seen and datetime.fromtimestamp(viewer_last_seen)
            viewer_sid = viewers_sid.get(viewer_id)

            rows.append(
                {
                    "streamer_id": streamer_id,
                    "streamer": streamer,
                    "streamer_last_seen": streamer_last_seen,
                    "streamer_sid": streamer_sid,
                    "viewer_id": viewer_id,
                    "viewer": viewer,
                    "viewer_last_seen": viewer_last_seen,
                    "viewer_sid": viewer_sid,
                }
            )

        rows.sort(key=lambda r: r["streamer_last_seen"] is None or r["streamer_last_seen"], reverse=True)
        return await self.templates.TemplateResponse(
            request,
            "admin/streamers_data.html",
            {"request": request, "rows": rows},
        )
