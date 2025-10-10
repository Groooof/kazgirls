from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from repository.user import UserRepository
from services.bases import BaseServiceAbstract


class UserService(BaseServiceAbstract):
    def __init__(self, db: AsyncSession):
        self.users = UserRepository(db)

    async def get_user_by_username(self, username: str) -> User | None:
        return await self.users.first(User.username == username)
