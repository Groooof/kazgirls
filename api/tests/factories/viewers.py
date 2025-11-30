from models.viewers import ViewerProfile
from tests.factories.bases import BaseSQLAlchemyFactory


class ViewerProfileFactory(BaseSQLAlchemyFactory[ViewerProfile]):
    avatar = None
    force_rating = None
    force_rating_votes = None
