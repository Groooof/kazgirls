# Project Backend

> Что за UV?

[Смотри тут](https://docs.astral.sh/uv/concepts/projects/dependencies/)

> А какие команды вызывать?

[Вот эти ](https://docs.astral.sh/uv/reference/cli/)

## Локальное Разворачивание

### 🔨 Запуск Backend

!!! Убедитесь, что у вас установлен UV в системе.

```bash
# Установить зависимости. Без флага Frozen Они обновятся.
uv sync --group local --frozen
```

#### Подготовка Базы Данных

- Удали \_\_abstract\_\_ = True из нужных моделей

- Создай миграции

```bash
make migrations
```

- **Проверь** и примени миграции

```bash
make migrate
```

#### Запуск локального сервера

Скопируй example.env, они автоматом подтянутся Pydantic-ом при запуске

```bash
cp example.env .env
```

Запусти uvicorn

```bash
make run
```

### Запуск тестов

Тесты параллельные, по дефолту 4 воркера

```bash
make test
```

**С покрытием**

```bash
make test-cov
```
