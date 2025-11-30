from pydantic import BaseModel, Field


class StreamerSchema(BaseModel):
    id: int
    name: str | None = None
    avatar_url: str | None = None
    rating: float | None = None


class ViewerSchema(BaseModel):
    id: int
    name: str | None = None


class StreamerMarkSchema(BaseModel):
    mark: int = Field(ge=1, le=5)
