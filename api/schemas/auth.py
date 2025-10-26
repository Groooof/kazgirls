from schemas.bases import SchemeBase


class LoginResponseSchema(SchemeBase):
    access_token: str


class LoginRequestSchema(SchemeBase):
    username: str
    password: str
