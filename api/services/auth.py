import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from models import User, UserSession
from repository.user import UserSessionRepository
from services.bases import BaseServiceAbstract
from utils.libs import utc_now


class UserSessionService(BaseServiceAbstract):
    def __init__(self, db: AsyncSession):
        self.sessions = UserSessionRepository(db)

    async def create_session(self, user_id: int, token: str, ttl: datetime.datetime) -> None:
        expired = utc_now() + ttl
        session = UserSession(user_id=user_id, token=token, expired=expired)
        await self.sessions.save(session)

    async def deactivate_session(self, token: str) -> None:
        values = {"is_active": False}
        await self.sessions.update(UserSession.token == token, values=values)

    async def get_user(self, token: str) -> User | None:
        session = await self.sessions.first(
            UserSession.token == token,
            UserSession.is_active,
            (UserSession.expired >= utc_now()),
            User.is_active,
            join=(User,),
            options=(contains_eager(UserSession.user),),
        )
        return session and session.user or None
