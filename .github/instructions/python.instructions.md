---
applyTo: "**/*.py"
---

# Python Coding Standards

## Async
- All DB, AI, and HTTP operations are `async def`.
- Use `await` — never `asyncio.run()` inside async code.
- Use `asyncio.wait_for()` for timeouts.

## Type Hints
- Every function has parameter and return type annotations.
- Use `X | None` over `Optional[X]`. Use `list[X]` over `List[X]`.
- Avoid `Any` — use `object` or a protocol when the type is truly unknown.

## Imports
- Group: stdlib → third-party → local. Blank line between groups.
- Use `from __future__ import annotations` in files with forward references.

## Error Handling
- No bare `except:`. Catch specific exceptions.
- AI calls return `None` on failure — handle it. Never silently drop.
- Use `logger.error()` / `logger.warning()` — never `print()`.

## Naming
- `snake_case` for functions, variables, modules.
- `PascalCase` for classes.
- `UPPER_SNAKE` for constants.
- Descriptive names — no single-letter vars except `i`, `e`, `k`, `v` in comprehensions.

## Pydantic
- Use Pydantic v2 (`BaseModel` / `BaseSettings`). No v1 patterns.
- `model_config = SettingsConfigDict(...)` for settings.
- `model_validator(mode="after")` for cross-field validation.

## SQLAlchemy
- Use 2.0 style: `Mapped[]`, `mapped_column()`, `select()`.
- No legacy `Column()`, `query()`, or implicit session patterns.

## Dependencies
- Constructor injection via `__init__`. No global state.
- Use `ServiceContainer` from `dependencies.py` as the composition root.
- Services receive repos, repos receive sessions.
