from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.auth import UserFactory
from tests.factories.streamers import StreamerProfileFactory
from tests.factories.viewers import ViewerProfileFactory


async def load_fixtures(session: AsyncSession):
    await _load_users(session)


async def _load_users(session: AsyncSession):
    session.add_all(
        (
            UserFactory.build(id=1, username="user", password="test"),  # simple user # noqa: S106
            UserFactory.build(id=2, username="admin", is_superuser=True),  # admin_user
            UserFactory.build(id=3, username="inactive", is_active=False),  # inactive user
            UserFactory.build(id=4, username="user_empty"),  # authed user without data
            UserFactory.build(id=5, username="streamer_1", password="test", is_streamer=True),  # noqa: S106
            UserFactory.build(id=6, username="streamer_2", password="test", is_streamer=True),  # noqa: S106
            UserFactory.build(id=7, username="viewer_1", password="test", is_streamer=False),  # noqa: S106
            UserFactory.build(id=8, username="viewer_2", password="test", is_streamer=False),  # noqa: S106
            UserFactory.build(id=9, username="viewer_3", password="test", is_streamer=False),  # noqa: S106
        )
    )
    session.add_all(
        (
            StreamerProfileFactory.build(id=1, user_id=5, name="Streamer 1", force_rating=4.546),
            StreamerProfileFactory.build(id=2, user_id=6, name="Streamer 2", force_rating=3.3),
        )
    )
    session.add_all(
        (
            ViewerProfileFactory.build(id=1, user_id=1, name="Viewer 1"),
            ViewerProfileFactory.build(id=2, user_id=2, name="Viewer 2"),
            ViewerProfileFactory.build(id=3, user_id=3, name="Viewer 3"),
            ViewerProfileFactory.build(id=4, user_id=4, name="Viewer 4"),
            ViewerProfileFactory.build(id=5, user_id=5, name="Viewer 5"),
            ViewerProfileFactory.build(id=6, user_id=6, name="Viewer 6"),
            ViewerProfileFactory.build(id=7, user_id=7, name="Viewer 7"),
            ViewerProfileFactory.build(id=8, user_id=8, name="Viewer 8"),
            ViewerProfileFactory.build(id=9, user_id=9, name="Viewer 9"),
        )
    )
    await session.commit()
