from collections.abc import Mapping, Sequence
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    from .dto import RequestTimeout

type PrimitiveData = str | int | float | bool | None

# requests
type URLTypes = str
type QueryParamTypes = (
    Mapping[str, PrimitiveData | Sequence[PrimitiveData]] | list[tuple[str, PrimitiveData]] | str | bytes
)
type HeaderTypes = Mapping[str, str]
type CookieTypes = dict[str, str]
type AuthTypes = tuple[str | bytes, str | bytes]
type TimeoutTypes = "float | RequestTimeout"

# files
type FileContent = IO[bytes] | bytes | str
type FileTypes = (
    # file (or bytes)
    FileContent
    |
    # (filename, file (or bytes))
    tuple[str | None, FileContent]
    |
    # (filename, file (or bytes), content_type)
    tuple[str | None, FileContent, str | None]
    |
    # (filename, file (or bytes), content_type, headers)
    tuple[str | None, FileContent, str | None, Mapping[str, str]]
)
type RequestFiles = Mapping[str, FileTypes] | Sequence[tuple[str, FileTypes]]
