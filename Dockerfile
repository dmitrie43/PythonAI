# Образ API-сервиса.
# Многостадийно не усложняем: python + uv + наш пакет.

FROM python:3.11-slim

WORKDIR /app

# Бинарь uv из официального образа (быстрый pip-аналог)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Компиляция bytecode при install; copy mode надёжнее в Docker volume-сценариях
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Сначала манифест, потом код — лучше кэш слоёв Docker при правках только src/
COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY alembic ./alembic

# Ставим зависимости и editable-пакет (появляются essentials-api / essentials-seed)
RUN uv sync --no-dev

EXPOSE 8000
# uvicorn импортирует объект app из essentials_lab.main
# При старте lifespan выполнит alembic upgrade head
CMD ["uvicorn", "essentials_lab.main:app", "--host", "0.0.0.0", "--port", "8000"]
