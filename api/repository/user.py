from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.orm import contains_eager

from exceptions.db import DoesNotExist, MultipleObjectsReturned
from models.user import User, UserSession
from repository.bases import BaseSQLRepository
from schemas.auth import TokenTypesChoices
from utils.libs import utc_now


class UserRepository(BaseSQLRepository[User]):
    async def get_user_by_username(self, username: str, select_for_update: bool = False) -> User:
        result = await self._filter(self.model.username == username, select_for_update=select_for_update)
        try:
            return result.one()
        except NoResultFound:
            raise DoesNotExist(self.model)
        except MultipleResultsFound:
            raise MultipleObjectsReturned(self.model)


class UserSessionRepository(BaseSQLRepository[UserSession]):
    async def get_active_user_session_by_token(self, token: str, token_type: TokenTypesChoices) -> UserSession | None:
        session = await self.first(
            UserSession.token == token,
            UserSession.token_type == token_type,
            UserSession.is_active,
            UserSession.expired.is_(None) | (UserSession.expired >= utc_now()),
            User.is_active,
            join=(User,),
            options=(contains_eager(UserSession.user),),
        )
        return session

    async def deactivate(self, token: str):
        await self.update(UserSession.token == token, values={"is_active": False})

    async def upload_to_storage(self, session: UserSession):
        self.add(session)
