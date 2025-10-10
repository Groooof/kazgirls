import io
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from json import JSONDecodeError
from typing import Any, BinaryIO

from httpx import HTTPError, Request, Response


class AsyncWrapper:
    def __init__(self, content: BinaryIO):
        self.content = content

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return

    async def read(self):
        return self.content.read()


class FakeFile:
    def __init__(self, path: str, content: BinaryIO | str | bytes):
        self.path = path
        match content:
            case str():
                content = io.BytesIO(content.encode())
            case bytes():
                content = io.BytesIO(content)
        self.content = content

    def __getitem__(self, item):
        if item == "Body":
            return AsyncWrapper(self.content)


class FakeS3Client:
    storage = {}
    exception: Exception | None = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def put_object(self, Bucket, Key, Body):
        if self.exception:
            raise self.exception
        self.storage[Key] = FakeFile(Key, Body)

    async def get_object(self, Bucket, Key):
        if self.exception:
            raise self.exception
        return self.storage.get(Key)

    async def delete_object(self, Bucket, Key):
        if self.exception:
            raise self.exception
        del self.storage[Key]

    async def head_object(self, Bucket, Key):
        if self.exception:
            raise self.exception
        data = self.storage[Key]
        return {"ContentLength": data.content.getbuffer().nbytes}

    async def generate_presigned_url(
        self,
        ClientMethod: str,
        Params: Mapping[str, Any] = ...,
        ExpiresIn: int = 3600,
        HttpMethod: str = ...,
    ):
        if self.exception:
            raise self.exception
        return f"http://fake.url/{Params['Key']}"


class FakeS3Session:
    def create_client(self, *args, **kwargs):
        return FakeS3Client(*args, **kwargs)


class FakeHttpxClient:
    def __init__(
        self,
        status_code: int = 200,
        json: dict | None = None,
        exc: HTTPError | None = None,
        *,
        multiple_responses: bool = False,
    ):
        self.status_code = status_code
        self.exception = exc
        self._json = json
        self._multiple = multiple_responses
        self._multiple_count = 0
        self._invalid_json_or_none = None

    @property
    def json(self):
        if not self._multiple:
            return self._json
        json = self._json[self._multiple_count]
        self._multiple_count += 1
        return json

    @json.setter
    def json(self, value):
        self._json = value

    @contextmanager
    def multiple_json(self, json: Sequence):
        old_json = self.json
        old_count = self._multiple_count
        self._multiple = True
        self.json = json
        try:
            yield
        finally:
            self._multiple = False
            self._multiple_count = old_count
            self.json = old_json

    @contextmanager
    def fake_error(self, exception: Exception | None = None, status_code: int | None = None):
        old_exception = self.exception
        old_status_code = self.status_code
        # клиент вернет такие ошибки только если выполнили .json(), поэтому в самом  request это не надо рейзить
        json_exception = isinstance(exception, JSONDecodeError)
        if exception and not json_exception:
            self.exception = exception
        elif exception and json_exception:
            self._invalid_json_or_none = "fake json response"
        if status_code is not None:
            self.status_code = status_code
        try:
            yield
        finally:
            self.exception = old_exception
            self.status_code = old_status_code
            self._invalid_json_or_none = None

    async def post(self, *args, **kwargs):
        if self.exception:
            raise self.exception
        request = Request("POST", kwargs.get("url", args[0]))
        return Response(
            status_code=self.status_code,
            json=self.json or {"data": {"clip_length": 11, "long_clip_hash": "qwerty", "emotion": None}},
            request=request,
            content=self._invalid_json_or_none,
        )

    async def patch(self, *args, **kwargs):
        if self.exception:
            raise self.exception
        request = Request("POST", kwargs.get("url", args[0]))
        return Response(
            status_code=self.status_code, json=self.json or {}, request=request, content=self._invalid_json_or_none
        )

    async def get(self, *args, **kwargs):
        if self.exception:
            raise self.exception
        request = Request("POST", kwargs.get("url", args[0]))
        return Response(
            status_code=self.status_code, json=self.json or {}, request=request, content=self._invalid_json_or_none
        )
