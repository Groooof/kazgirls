from datetime import datetime, timedelta

from freezegun import freeze_time

from logic.streamers import connect_streamer, get_free_online_streamers, get_free_online_streamers_ids, ping_streamer
from logic.viewers import clean_offline_viewers, connect_viewer
from schemas.streamers import StreamerSchema
from tests.custom_faker import fake_sid


async def test_get_free_online_streamers_ids(redis, sio):
    streamers_ids = await get_free_online_streamers_ids(redis)
    assert set(streamers_ids) == set()

    await connect_streamer(sio, redis, 5, fake_sid())
    streamers_ids = await get_free_online_streamers_ids(redis)
    assert set(streamers_ids) == {5}

    await connect_viewer(sio, redis, 7, fake_sid(), 5)
    streamers_ids = await get_free_online_streamers_ids(redis)
    assert set(streamers_ids) == set()

    await connect_streamer(sio, redis, 6, fake_sid())
    streamers_ids = await get_free_online_streamers_ids(redis)
    assert set(streamers_ids) == {6}

    with freeze_time(datetime.now() + timedelta(minutes=5)):
        await ping_streamer(redis, 5)
        await ping_streamer(redis, 6)
        await clean_offline_viewers(sio, redis)

    streamers_ids = await get_free_online_streamers_ids(redis)
    assert set(streamers_ids) == {5, 6}


async def test_get_free_online_streamers(sio, db, redis):
    await connect_streamer(sio, redis, 1, fake_sid())
    await connect_streamer(sio, redis, 2, fake_sid())

    expected_streamers = [
        StreamerSchema(id=1, name="Streamer 1", rating=4.55),
        StreamerSchema(id=2, name="Streamer 2", rating=3.3),
    ]
    streamers = await get_free_online_streamers(db, redis)
    assert streamers == expected_streamers
