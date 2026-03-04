# Skill: Testing Strategy

## Stack
- **Framework:** pytest + pytest-asyncio (auto mode)
- **DB tests:** In-memory SQLite via aiosqlite + StaticPool
- **Config:** `pytest.ini` — `asyncio_mode = auto`, `testpaths = tests`
- **No UI framework** — This is a Telegram bot backend, not a desktop/web app

## Test Organization
```
tests/
├── conftest.py         # Shared fixtures: db_session, async_session, fake_ptb_app
├── unit/               # Fast, isolated, no external deps
│   ├── test_ai_wrapper.py
│   ├── test_keyboards.py
│   ├── test_schemas.py
│   └── test_trend.py
├── integration/        # DB + service layer tests
└── contract/           # AI prompt contract tests
```

## Key Fixtures (`tests/conftest.py`)
- **`db_session`** — In-memory SQLite `AsyncSession` with all tables created. Use for any DB test.
- **`async_session`** — Alias for `db_session` (backward compat).
- **`fake_ptb_app`** — Minimal PTB Application with `FAKE:TOKEN`. Use for handler integration tests.
- Test env vars are set at module level before any imports (TELEGRAM_TOKEN, AZURE_OPENAI_KEY, etc. all use fake values).

## Testing Patterns

### Repository Tests
```python
async def test_create_goal(db_session):
    repo = GoalRepository(db_session)
    goal = await repo.create(GoalCreate(title="Test", ...))
    assert goal.id is not None
```

### Service Tests (with DI)
```python
async def test_service(db_session):
    svcs = service_scope(db_session)
    result = await svcs.goal.create_goal(user_id=1, data=GoalCreate(...))
    assert result.title == "Test"
```

### AI Wrapper Tests (mock OpenAI)
- Mock `AsyncAzureOpenAI` client
- Test: successful call, timeout, JSON parse error, missing config → all return None or valid dict
- Verify retries and exponential backoff

### Flow Tests
- Test step rendering and state transitions
- Mock `session_factory` in `bot_data`
- Use `FlowContext` with mocked PTB `Update` and `ContextTypes`

## Rules
1. **Arrange-Act-Assert** — Every test follows this structure
2. **Test behavior, not implementation** — Assert on outcomes, not internal calls
3. **Naming:** `test_<what>_<condition>_<expected_result>`
4. **One assert focus per test** — A test should have one clear reason to fail
5. **No flaky tests** — All tests must be deterministic (use freezegun for time)
6. **pytest-asyncio auto mode** — Just write `async def test_...` — no decorator needed
7. **Factory over complex fixtures** — Prefer helper functions that create test data
