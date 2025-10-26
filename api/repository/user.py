from models.user import User, UserSession
from repository.bases import BaseSQLRepository


class UserRepository(BaseSQLRepository[User]):
    pass


class UserSessionRepository(BaseSQLRepository[UserSession]):
    pass
