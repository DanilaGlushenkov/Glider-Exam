# Skill: Telegram Bot Patterns

## Architecture
The bot layer sits on top of the service layer. It handles Telegram-specific concerns (PTB types, keyboards, message rendering) and delegates all business logic to services via `ServiceContainer`.

### Layer Contract
- **Bot layer knows:** PTB types (`Update`, `ContextTypes`), `FlowContext`, `StepResult`, keyboard builders
- **Bot layer does NOT know:** SQLAlchemy, AI internals, HTTP clients

## DialogFlow System (`bot/flows/base.py`)

### Core Types
- **`DialogFlow`** (ABC) — Multi-step conversation base class. Subclasses declare `command`, `allowed_modes`, `steps`. `build()` auto-wires `ConversationHandler`.
- **`DialogStep`** (Protocol) — Each step implements `state_id: int`, `render()`, `handle_message()`, and/or `handle_callback()`.
- **`StepResult`** — Typed return from every step handler:
  - `StepResult.stay(current)` — validation failed, re-render
  - `StepResult.goto(state)` — advance to specific state
  - `StepResult.done()` — end conversation
  - `StepResult.wait()` — waiting for async callback
- **`FlowContext`** — Wraps PTB context with typed Pydantic state access via `get_state(Model)` / `set_state(model)` / `clear_state()`. Exposes `session_factory` from `bot_data`.

### Flow Implementation Pattern
```python
class MyFlow(DialogFlow):
    command = "mycommand"
    allowed_modes = ["tracking"]
    steps = [Step1(), Step2()]

class Step1:
    state_id = 0
    async def render(self, update, ctx): ...
    async def handle_callback(self, update, ctx) -> StepResult:
        # do work
        return StepResult.goto(Step2.state_id)
```

### State Management
- Flow state stored as Pydantic model in `context.user_data["_flow_state"]`
- Use `ctx.get_state(MyStateModel)` / `ctx.set_state(model)` — never access user_data directly
- `ctx.clear_state()` on cancel or done

## Mode Gate (`bot/mode_gate.py`)
- `@require_mode("tracking")` — decorator that gates commands by `user.mode`
- Multiple modes: `@require_mode("planning", "tracking")`
- **Every handler MUST have a mode gate** — missing it is an architecture violation
- If user's mode doesn't match, sends a human-readable hint and blocks execution

## Keyboards (`bot/keyboards.py`)
- Functions return `InlineKeyboardMarkup` for Telegram inline buttons
- Callback data format: short string identifiers (e.g. `"area:career"`, `"confirm:yes"`)

## Renderer (`bot/renderer.py`)
- Formats domain data into Telegram-friendly messages
- Handles Markdown escaping, message length limits
- Pure formatting — no DB or AI calls

## Concrete Flows
- `setup.py` — New user onboarding (planning mode)
- `add_goal.py` — Add a new goal (planning mode)
- `checkin.py` — Weekly check-in (tracking mode)
- `review.py` / `review_base.py` / `review_monthly.py` / `review_quarterly.py` / `review_yearend.py` — Review flows (milestone_review mode)
- `tracking_setup.py` — Tracking preferences setup
- `dashboard.py` — Goal dashboard display

## Handlers (`bot/handlers/`)
- `commands.py` — Slash command handlers (e.g. `/help`, `/goals`)
- `common.py` — Shared handler utilities
