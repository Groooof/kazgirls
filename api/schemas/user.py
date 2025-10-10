from schemas.bases import SchemeBase


class UserSchema(SchemeBase):
    id: int
    username: str
    is_superuser: bool
