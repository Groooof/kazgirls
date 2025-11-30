from enum import Enum


class Tags(str, Enum):
    auth_private = "Авторизация Внутренняя"
    streamers = "Стримеры"
    viewers = "Зрители"
    messages = "Сообщения"


base_tags_description = {
    Tags.auth_private: "Управление токеном",
    Tags.streamers: "Стримеры",
    Tags.viewers: "Зрители",
    Tags.messages: "Сообщения",
}
