from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


{
    "streamers:online": {
        "1": 1234567890,
        "2": 1234567890,
    },
    "streamers:1:viewers": {
        "1": 1234567890,
    },
    "streamers:1:data": {
        "is_busy": 1,
    },
}


class Streamer:
    user_id: int
    status: str  # online | offline
