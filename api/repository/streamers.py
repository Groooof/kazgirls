from models.streamers import StreamerMark, StreamerProfile
from repository.bases import BaseSQLRepository


class StreamerProfileRepository(BaseSQLRepository[StreamerProfile]):
    pass


class StreamerMarkRepository(BaseSQLRepository[StreamerMark]):
    pass
