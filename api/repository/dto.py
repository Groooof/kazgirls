from pydantic import BaseModel, ConfigDict


class UnsetType:
    pass


UNSET = UnsetType()


class RequestTimeout(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    connect: None | float | UnsetType = UNSET
    read: None | float | UnsetType = UNSET
    write: None | float | UnsetType = UNSET
    pool: None | float | UnsetType = UNSET
