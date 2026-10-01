"""
py-essentials-lab — учебный async API тикетов поддержки.

Слои (снизу вверх), как в аккуратном Laravel:
  domain.py      → чистая модель / бизнес-правила без БД и HTTP
  db/            → таблицы (Eloquent-like ORM)
  repositories   → SQL-запросы
  cache.py       → Redis
  services.py    → оркестрация (Action / Service)
  schemas.py     → валидация входа/выхода (Form Request + Resource)
  api/           → HTTP-контроллеры (routes)
  main.py        → точка входа FastAPI + lifespan
  cli.py         → artisan-подобный seed
"""

__version__ = "0.1.0"
