FROM python:3.13-slim-bookworm AS  base
COPY --from=ghcr.io/astral-sh/uv:0.8.4 /uv /uvx /bin/

ENV PATH="/code/.venv/bin:$PATH"
# UV_PYTHON_DOWNLOADS — отключает автоматическую загрузку отсутствующих версий Python.
# UV_LINK_MODE — меняет способ установки пакетов из глобального кэша.
#   Вместо создания жёстких ссылок, файлы пакета копируются в директорию  виртуального окружения `site-packages`.
#   Это необходимо для будущего копирования изолированной `/app` директории из  стадии `build` в финальный Docker-образ.
# PYTHONOPTIMIZE — убирает инструкции `assert` и код, зависящий от значения  константы `__debug__`,
#   при компиляции файлов Python в байт-код.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PYTHONOPTIMIZE=1

# в этом образе устанавливаем и собираем пакеты
FROM base AS py-builder

WORKDIR /code

RUN apt update -qq \
    && apt install -y -qq \
        make \
        nano \
        git \
        vim

RUN apt clean -y && apt autoremove -y \
    && rm -rf /var/lib/apt/list \
    && rm -rf /var/cache/apt

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1

COPY .. .

# Устанавливаем зависимости
FROM py-builder AS py-builder-required-packages

RUN uv sync --frozen

FROM py-builder AS py-builder-all-packages

RUN uv sync --dev --frozen

# Финальные образы, зависимости копируем из предыдущего эпата.
FROM py-builder AS api-test
COPY --from=py-builder-all-packages /code/.venv /code/.venv

FROM py-builder AS api-local
WORKDIR /code

COPY --from=py-builder-required-packages /code/.venv /code/.venv

STOPSIGNAL SIGINT

CMD ["uvicorn", "--factory", "--reload", "--proxy-headers", "--forwarded-allow-ips", "*", "app:get_app", "--host", "0.0.0.0", "--port", "8002"]

FROM py-builder AS api-prod
WORKDIR /code

COPY --from=py-builder-required-packages /code/.venv /code/.venv

STOPSIGNAL SIGINT

ENTRYPOINT ["uvicorn", "--factory", "--proxy-headers", "--forwarded-allow-ips", "*", "app:get_app", "--host", "0.0.0.0", "--port", "8002"]
