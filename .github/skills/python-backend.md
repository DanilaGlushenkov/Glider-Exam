# Skill: Python Backend

## Tech Stack
- **Runtime:** Python 3.12+ (fully async)
- **Web framework:** FastAPI 0.111 + Uvicorn
- **ORM:** SQLAlchemy 2.0 async (`AsyncSession`, `async_sessionmaker`)
- **DB:** PostgreSQL (prod via asyncpg) / SQLite (tests via aiosqlite)
- **Migrations:** Alembic
- **Telegram:** python-telegram-bot 21.x (PTB)
- **AI:** Azure OpenAI (via `openai` SDK, `AsyncAzureOpenAI` client)
- **Cache/state:** Redis 5.x
- **Validation:** Pydantic v2 + pydantic-settings
- **Config:** `config.py` → `Settings(BaseSettings)` loaded from `.env`
- **Testing:** pytest + pytest-asyncio (auto mode)

## Project Structure
```
main.py              # FastAPI app + PTB webhook setup
config.py            # Settings(BaseSettings) — single source of env config
dependencies.py      # ServiceContainer: session → repos → services composition root
ai/wrapper.py        # call_skill() — never-raises AI caller (returns None on failure)
ai/prompts/*.yaml    # Skill YAML files (system + user prompt templates)
helpers/prompt_cache.py  # Loads & caches YAML prompts by skill name
bot/flows/base.py    # DialogFlow ABC, DialogStep Protocol, StepResult, FlowContext
bot/flows/*.py       # Concrete flows (setup, checkin, review, add_goal, etc.)
bot/handlers/        # Command handlers + common utilities
bot/mode_gate.py     # @require_mode() decorator — gates commands by user.mode
bot/keyboards.py     # InlineKeyboardMarkup builders for Telegram
bot/renderer.py      # Message formatting for Telegram output
db/models/           # SQLAlchemy ORM models (one file per entity)
db/repositories/     # One repo class per entity, AsyncSession injected via __init__
db/session.py        # Engine + session factory creation
services/            # One service class per domain concept, repos injected via __init__
schemas/             # Pydantic schemas for API/AI boundaries
workers/             # Background workers + scheduler
utils/               # Cross-cutting utilities (e.g. redis_persistence)
```

## Key Conventions
1. **Async everywhere** — All DB, AI, and HTTP operations are `async def`.
2. **Dependency Injection** — Constructor injection. No global session creation inside services/repos. Use `ServiceContainer` from `dependencies.py`.
3. **Never raise from AI** — `call_skill()` catches all exceptions and returns `None`. Services must handle `None` gracefully.
4. **Pydantic for validation** — All external data boundaries use Pydantic v2 models.
5. **Type hints required** — Every function has return annotations. Avoid `Any` unless truly needed.
6. **Module-level backward-compat wrappers** — Repo/service classes have standalone async functions wrapping the class pattern for existing callers.
7. **No PTB types in services** — `Update`, `ContextTypes` never appear below the bot layer.
8. **Config via `get_settings()`** — Uses `@lru_cache` singleton. Never read `os.environ` directly in application code.
