from pydantic import BaseModel


class StreamerSchema(BaseModel):
    id: int
    name: str
    avatar_url: str | None = None
    rating: float | None = None
