from enum import Enum


class Tags(str, Enum):
    auth_private = "Авторизация Внутренняя"
    lobby = "Лобби"


base_tags_description = {
    Tags.auth_private: "Управление токеном",
    Tags.lobby: "Лобби",
}
