from fastapi import status
from httpx import AsyncClient

from settings import conf


async def test_user(client: AsyncClient):
    # неверный логин пароль
    url = "/tokens/login"
    response = await client.post(url, json={"username": "fake", "password": "fake"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, response.text

    # невалидные данные
    response = await client.post(url, json={"fake": "fake"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, response.text

    response = await client.post(url, json={"username": "user", "password": "test"})
    assert response.status_code == status.HTTP_200_OK, response.text
    token = response.json()["access_token"]
    assert token

    #  неактивный юзер
    response = await client.post(url, json={"username": "inactive", "password": "password"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, response.text

    # невалидный токен
    headers = {"Authorization": "Bearer 123"}
    response = await client.get("/tokens/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, response.text

    # невалидная схема авторизации
    headers = {"Authorization": ""}
    response = await client.get("/tokens/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, response.text

    # токен для апи не создавали
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/tokens/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, response.text

    response = await client.get("/tokens/me", cookies={conf.other_settings.access_token_cookie_name: token})
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"id": 1, "username": "user", "is_superuser": False, "is_streamer": False}
