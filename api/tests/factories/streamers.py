from models.streamers import StreamerProfile
from tests.factories.bases import BaseSQLAlchemyFactory


class StreamerProfileFactory(BaseSQLAlchemyFactory[StreamerProfile]):
    avatar = None
    force_rating = None
    force_rating_votes = None
