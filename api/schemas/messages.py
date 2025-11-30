from datetime import datetime

from pydantic import BaseModel, field_serializer


class MessageSchema(BaseModel):
    created: datetime
    from_streamer: bool
    text: str

    @field_serializer("created")
    def serialize_created(self, value: datetime, _info):
        return value.strftime("%Y-%m-%d %H:%M:%S")
