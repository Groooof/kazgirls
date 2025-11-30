from sqlalchemy.ext.asyncio.session import AsyncSession

from exceptions.bases import Http404
from models.viewers import ViewerProfile
from repository.viewers import ViewerProfileRepository
from schemas.streamers import ViewerSchema


def _get_viewer_schema_from_obj(viewer: ViewerProfile) -> ViewerSchema:
    return ViewerSchema(id=viewer.id, name=viewer.name)


async def get_viewer(db: AsyncSession, viewer_id: int) -> ViewerSchema:
    repo = ViewerProfileRepository(db)
    viewer = await repo.first(ViewerProfile.id == viewer_id)
    if not viewer:
        raise Http404

    return _get_viewer_schema_from_obj(viewer)
