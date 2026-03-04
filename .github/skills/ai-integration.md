# Skill: AI Integration

## Architecture
The AI layer is isolated behind `ai/wrapper.py`. No other layer calls OpenAI directly. Services call `call_skill()`, which is the single entry point.

## AI Wrapper (`ai/wrapper.py`)

### `call_skill(skill: str, variables: dict) -> dict | None`
- **Never raises** — catches all exceptions, logs them, returns `None`
- Retries with exponential backoff (configurable: `AI_MAX_RETRIES`, `AI_RETRY_BASE_DELAY`)
- 10-second timeout per attempt
- Forces `response_format={"type": "json_object"}` — all AI responses are parsed JSON
- Uses singleton `AsyncAzureOpenAI` client (connection reuse)

### Invariant: AI Failure Is Never a Flow Failure
When `call_skill()` returns `None`, the calling service MUST:
- Use the prompt's `fallback` value, OR
- Skip AI output and continue the flow normally
- **Never crash or leave the user in a broken state**

## Prompt System (`ai/prompts/*.yaml`)

### YAML Structure
```yaml
version: "1.0"
skill: weekly_coach          # lookup key for get_prompt()
max_tokens: 400
system_prompt: |
  You are a ... [role description + rules + output schema]
user_prompt_template: |
  {variable_name_1}
  {variable_name_2}
fallback:
  reply: "Default message if AI fails"
```

### Prompt Cache (`helpers/prompt_cache.py`)
- `get_prompt(skill)` — returns cached YAML dict by skill name
- Auto-loads all `ai/prompts/*.yaml` on first call
- Skill name comes from the `skill:` field inside the YAML, not the filename

### Available Skills
| Skill | Purpose | Key Variables |
|-------|---------|---------------|
| `weekly_coach` | Weekly check-in coaching | `goals_with_why`, `signals`, `note`, `trend` |
| `planning_coach` | Goal planning co-author | varies |
| `milestone_reviewer` | Milestone review assessment | varies |
| `balance_check_v1` | Plan balance analysis | varies |
| `goal_structurer_v1` | Goal structuring | varies |
| `tracking_advisor_v1` | Tracking advice | varies |
| `quarterly_review_v1` | Quarterly review | varies |
| `yearend_review_v1` | Year-end review | varies |

## Adding a New Skill
1. Create `ai/prompts/my_skill.yaml` following the YAML structure above
2. Set `skill: my_skill` inside the file
3. Define `system_prompt` with role, rules, and JSON output schema
4. Define `user_prompt_template` with `{variable}` placeholders
5. Add `fallback:` with sensible default response
6. Call from service: `result = await call_skill("my_skill", {"var": value})`
7. Handle `None` return gracefully

## Rules
- AI is called ONLY through `call_skill()` — never instantiate OpenAI clients elsewhere
- All prompts return JSON — always define an output schema in the system prompt
- `why` field on goals is AI-context-only — never expose it to the user
- Prompt variable names must match exactly between YAML template and service call
