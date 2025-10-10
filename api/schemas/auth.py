from schemas.bases import SchemeBase, TextChoices

type Timestamp = int
type Username = str


class TokenTypesChoices(TextChoices):
    session = "session", "Session"  # Frontend Session
    api = "api", "API"  # Авторизация по заголовку


class AccessTokenSchema(SchemeBase):
    access_token: str


class JWTSessionPayloadSchema(SchemeBase):
    sub: Username
    user_id: int
    token_type: TokenTypesChoices
    exp: Timestamp | None = None


class LoginSchema(SchemeBase):
    username: Username
    password: str
