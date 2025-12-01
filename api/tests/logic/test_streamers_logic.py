from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from freezegun import freeze_time

from exceptions.streamers import NoSeatsError
from logic.auth import login_user_by_password
from logic.streamers import clean_offline_streamers, connect_streamer, ping_streamer
from logic.viewers import clean_offline_viewers, connect_viewer, ping_viewer
from sockets.streamers import connect
from tests.custom_faker import fake_sid
from utils.libs import utc_now


async def test_connect_streamer(sio, redis):
    await connect_streamer(sio, redis, 5, fake_sid())


async def test_connect_viewer(redis, sio):
    await connect_viewer(sio, redis, 7, fake_sid(), 6)
    await connect_viewer(sio, redis, 7, fake_sid(), 5)
    await connect_viewer(sio, redis, 7, fake_sid(), 5)
    await connect_viewer(sio, redis, 8, fake_sid(), 6)

    with pytest.raises(NoSeatsError):
        await connect_viewer(sio, redis, 8, fake_sid(), 5)


async def test_ping_streamer(redis):
    await ping_streamer(redis, 5)


async def test_ping_viewer(redis):
    await ping_viewer(redis, 7)


async def test_clean_offline_viewers(redis, sio):
    await connect_streamer(sio, redis, 5, fake_sid())
    await connect_streamer(sio, redis, 6, fake_sid())

    await connect_viewer(sio, redis, 7, fake_sid(), 5)
    await connect_viewer(sio, redis, 8, fake_sid(), 6)

    with freeze_time(utc_now() + timedelta(minutes=2)):
        await ping_viewer(redis, 8)
        await clean_offline_viewers(sio, redis)


async def test_clean_offline_streamers(sio, redis):
    await connect_streamer(sio, redis, 5, fake_sid())
    await connect_streamer(sio, redis, 6, fake_sid())

    with freeze_time(utc_now() + timedelta(minutes=2)):
        await ping_streamer(redis, 5)
        await clean_offline_streamers(sio, redis)


async def test_streamers_connect(db, redis):
    sio = AsyncMock()
    sid = fake_sid()
    token = await login_user_by_password(db, "streamer_1", "test")
    await connect(sid, {"HTTP_COOKIE": f"access_token={token}; test=test;"}, {}, db=db, redis=redis, sio=sio)
