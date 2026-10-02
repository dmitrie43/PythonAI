# py-essentials-lab — мини-тренажёр Python для PHP/Laravel-разработчика

Один сервис закрывает то, что нужно до FastAPI/RAG по плану:

| Тема | Где в коде | Аналог в Laravel |
|------|------------|------------------|
| Классы / dataclass / enum | `domain.py` | DTO / Enum |
| Pydantic-схемы | `schemas.py` | Form Request + API Resource |
| Async I/O | везде `async def` | реже; тут норма для API |
| PostgreSQL (SQLAlchemy 2) | `db/`, `repositories.py` | Eloquent / Query Builder |
| Redis-кэш | `cache.py` | `Cache::remember` |
| Слои: repo → service → HTTP | `repositories` / `services` / `api` | Repository + Action + Controller |
| DI / lifespan | `api/deps.py`, `main.py` | Service Container + providers |
| CLI + asyncio | `cli.py` | `artisan` command |
| Docker Compose | `docker-compose.yml` | Sail / свой compose |
| Middleware + rate limit | `api/middleware.py` | Middleware + `RateLimiter` |
| Миграции БД | `alembic/` | Laravel migrations |
| Тесты | `tests/` | PHPUnit / Pest |

Домен: **тикеты поддержки + заметки** (задел под пилот Docs/Ticket Assistant).

## Быстрый старт (Docker)

```powershell
cd C:\Docker\ai\py-essentials-lab
docker compose up --build -d
```

Проверка:

```powershell
curl http://127.0.0.1:8000/api/health
```

pgAdmin: http://127.0.0.1:5050  
Логин: `admin@example.com` / `admin`  
Сервер уже в списке (`essentials (docker)`); пароль БД при подключении: `essentials`.

Сиды:

```powershell
docker compose exec api essentials-seed -n 5
```

Примеры API:

```powershell
# создать тикет
curl -X POST http://127.0.0.1:8000/api/tickets `
  -H "Content-Type: application/json" `
  -d "{\"title\":\"VPN broken for new hire\",\"priority\":2}"

# список
curl http://127.0.0.1:8000/api/tickets

# получить (второй запрос придёт из Redis, поле cached=true)
curl http://127.0.0.1:8000/api/tickets/1
```

Swagger UI: http://127.0.0.1:8000/docs

Остановка:

```powershell
docker compose down
```

## Локально через uv (без Docker-образа API)

Поднять только инфраструктуру:

```powershell
docker compose up -d db redis
copy .env.example .env
uv sync
uv run essentials-api
# в другом терминале:
uv run essentials-seed -n 3
uv run pytest
```

## Структура

```
src/essentials_lab/
  domain.py          # чистая доменная модель
  schemas.py         # вход/выход API
  db/models.py       # ORM
  repositories.py    # SQL
  cache.py           # Redis
  services.py        # бизнес-правила
  api/routes.py      # HTTP
  api/middleware.py  # Request-ID + Redis rate limit
  main.py            # FastAPI app
  cli.py             # async seed

alembic/
  versions/          # миграции схемы (≈ database/migrations)
  env.py             # связь с Base.metadata + DATABASE_URL
```

## Alembic (миграции)

При старте API lifespan делает `alembic upgrade head` (как `artisan migrate`).

```powershell
# вручную
uv run alembic upgrade head
uv run alembic current
uv run alembic revision --autogenerate -m "add something"
# или
uv run essentials-migrate
```

Если раньше таблицы создавались через `create_all` без alembic_version — проще пересоздать том:

```powershell
docker compose down -v
docker compose up --build -d
```

## Middleware / rate limit

- `X-Request-ID` — на каждом ответе (можно прислать свой в заголовке запроса)
- `X-RateLimit-Limit` / `Remaining` / `Reset` — на API-запросах
- сверх лимита → **429** + `Retry-After`
- `/api/health` и `/docs` не лимитируются
- настройки: `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` (см. `.env.example`)

## Что проговорить вслух после прогона (чеклист обучения)

1. Чем `dataclass` Ticket отличается от `TicketModel` (ORM)?
2. Почему `get_ticket` сначала смотрит Redis?
3. Где живёт правило «нельзя писать в resolved» — и почему не в роуте?
4. Что делают `async with session` и `lifespan`?
5. Как бы Laravel-контроллер вызвал этот API?

## Тесты

```powershell
# юнит-тесты домена — всегда
uv run pytest tests/test_domain.py -q

# интеграция — нужен поднятый compose
docker compose up --build -d
uv run pytest tests/test_api_integration.py -q
```
