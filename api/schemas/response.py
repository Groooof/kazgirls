from pydantic import Field

from schemas.bases import SchemeBase


class ErrorStruct(SchemeBase):
    message: str = Field(..., serialization_alias="description", description="Описание события")
    details: dict | None = Field(None, description="Дополнительная информация")
    documentation_url: str | None = Field(None, description="Ссылка на документацию")
