# Skill: Database Patterns

## Models (`db/models/`)
- One file per entity: `user.py`, `goal.py`, `milestone.py`, `checkin.py`, `milestone_review.py`, `plan.py`, `conversation.py`
- All inherit from `Base` in `db/models/base.py`
- Use SQLAlchemy 2.0 `Mapped[]` / `mapped_column()` style — no legacy `Column()` calls
- Enums: Python `enum.Enum` subclass → `sa.Enum(MyEnum)` column
- Timestamps: `created_at`, `updated_at` with timezone-aware `DateTime(timezone=True)`
- JSONB for flexible data: e.g. `checkins.signals` stores `{goal_id: signal, ...}`

## Entity Relationships
```
User ──< Goal ──< Milestone
              └─< CheckIn
              └─< MilestoneReview
```

### Key Enums
- `UserMode`: `planning`, `tracking`, `milestone_review`
- `GoalStatus`: `active`, `paused`, `archived`
- `GoalArea`: `career`, `health`, `relationships`, `finance`, `personal_growth`, `fun`
- `MilestoneOutcome`: `completed`, `missed`, `revised`

## Repository Layer (`db/repositories/`)
- **One class per entity**, receives `AsyncSession` in `__init__`
- Returns ORM model instances, lists, or `None` — never dicts
- **No business logic, no AI calls, no logging of app events**
- Module-level wrapper functions for backward compatibility:
```python
class GoalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
    async def get_by_id(self, goal_id: int) -> Goal | None: ...

# Backward-compat wrapper
async def get_by_id(session: AsyncSession, goal_id: int) -> Goal | None:
    return await GoalRepository(session).get_by_id(goal_id)
```

## Service Layer (`services/`)
- **One class per domain concept**, receives repo(s) in `__init__`
- Orchestrates repos + AI calls. Returns domain objects.
- Session is **never opened here** — always passed from bot layer via `ServiceContainer`
- AI called only via `ai.wrapper.call_skill()` — never directly
- Module-level backward-compat wrappers same pattern as repos

## Composition Root (`dependencies.py`)
```python
class ServiceContainer:
    def __init__(self, session: AsyncSession) -> None:
        # repos
        self.user_repo = UserRepository(session)
        self.goal_repo = GoalRepository(session)
        # ... etc
        # services
        self.user = UserService(self.user_repo)
        self.goal = GoalService(self.goal_repo)
        # ... etc
```
Usage: `service_scope(session)` or `async with request_scope(factory) as svcs:`

## Alembic Migrations (`alembic/versions/`)
- Sequential numbering: `001_initial.py`, `002_add_tone_enum.py`, etc.
- Config: `alembic.ini` points to `DATABASE_URL_SYNC`
- Run: `alembic upgrade head` / `alembic revision --autogenerate -m "..."`
- **Always test migrations against the current state before committing**
