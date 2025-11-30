from models.messages import Message
from repository.bases import BaseSQLRepository


class MessageRepository(BaseSQLRepository[Message]):
    pass
