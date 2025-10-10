from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.auth import UserFactory


async def load_fixtures(session: AsyncSession):
    await _load_users(session)


async def _load_users(session: AsyncSession):
    session.add_all(
        (
            UserFactory.build(id=1, username="user", password="test"),  # simple user # noqa: S106
            UserFactory.build(id=2, username="admin", is_superuser=True),  # admin_user
            UserFactory.build(id=3, username="inactive", is_active=False),  # inactive user
            UserFactory.build(id=4, username="user_empty"),  # authed user without data
        )
    )
    await session.commit()
