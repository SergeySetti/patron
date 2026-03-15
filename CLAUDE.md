# Patron — Project Context for Claude

## What Is This?

Telegram bot acting as a personal planning & memory assistant. Built with **LangChain + Google Gemini 3.1 Pro**, persists state in **MongoDB** and vectors in **Qdrant**.

Owner: **Sergii Setti** (`serhii.setti@pm.me`)

---

## Architecture at a Glance

```
bot.py (Telegram entry point)
  ├── /start handler
  ├── /subscribe handler → Telegram Stars invoice
  ├── PreCheckoutQueryHandler → approve payment
  ├── SUCCESSFUL_PAYMENT handler → record transaction + extend subscription
  ├── message handler → subscription check → run_agent()
  └── job queue (60s) → check_due_tasks() → run_agent() (no subscription check)

patron_agent.py (Agent orchestration)
  ├── CustomAgentState: user_id, chat_id, preferences, user_timezone
  ├── System prompt: includes current UTC time + user timezone context
  ├── Tools: memory, task, user, get_weather (mock)
  └── Checkpointer: MongoDBSaver (multi-turn conversations)

dependencies.py (DI container via `injector`)
  ├── VectorizerGemini (768-dim embeddings)
  ├── QdrantClient
  └── MongoClient
```

## Key Files

| File                                                           | Purpose                                                                                                   |
|----------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `src/bot.py`                                                   | Telegram bot entry point, handlers, payment flow, job queue                                               |
| `src/task_scheduler.py`                                        | `check_due_tasks()` — polls DB every 60s for due tasks                                                    |
| `src/dependencies.py`                                          | DI container (`app_container`), binds Qdrant/Mongo/Vectorizer                                             |
| `src/agents/patron_itself/patron_agent.py`                     | Agent creation, system prompt, `run_agent()`                                                              |
| `src/agents/patron_itself/repositories/tasks_repository.py`    | MongoDB: `patron_tasks.tasks`                                                                             |
| `src/agents/patron_itself/repositories/users_repository.py`    | MongoDB: `patron_users.users` (timezone, subscription)                                                    |
| `src/agents/patron_itself/repositories/transactions_repository.py` | MongoDB: `patron_users.transactions` (payment records)                                                |
| `src/agents/patron_itself/repositories/memories_repository.py` | Qdrant: `memories` collection (768-dim cosine)                                                            |
| `src/agents/patron_itself/tools/task_tools.py`                 | `create_task`, `list_tasks`, `delete_task`                                                                |
| `src/agents/patron_itself/tools/user_tools.py`                 | `get_user_timezone`, `set_user_timezone`                                                                  |
| `src/agents/patron_itself/tools/memory_tools.py`               | `add_memory`, `recall_memories_by_semantic_query`, `recall_memories_by_time_constraints`, `delete_memory` |
| `src/services/vectorisation/VectorizerGemini.py`               | Google Gemini embedding wrapper                                                                           |

## Repositories

### TasksRepository (MongoDB: `patron_tasks.tasks`)
- `create(user_id, chat_id, text, due_at)` → task_id (UUID)
- `get_due_tasks(now)` → pending tasks where `due_at <= now`
- `mark_completed(task_id)` — sets status + completed_at
- `get_tasks_for_user(user_id, status=None)`
- `delete(task_id)` → bool
- Indexes: `user_id`, `(due_at, status)`

### UsersRepository (MongoDB: `patron_users.users`)
- `get(user_id)` → full user doc or None
- `get_timezone(user_id)` → IANA string or None
- `set_timezone(user_id, timezone)` — upsert
- `get_subscription_status(user_id)` → `"active"` if `subscription_expires_at` is in the future, else `None`
- `get_subscription_expires_at(user_id)` → datetime or None
- `extend_subscription(user_id)` → adds 30 days (stacks on remaining time if active, starts from now if expired)
- Index: `user_id` (unique)

### TransactionsRepository (MongoDB: `patron_users.transactions`)
- `create(user_id, telegram_payment_charge_id, provider_payment_charge_id, total_amount, currency, is_recurring)` → inserted id
- `get_by_user(user_id)` → list of transactions, newest first
- `get_by_charge_id(telegram_payment_charge_id)` → transaction or None
- Indexes: `user_id`, `telegram_payment_charge_id` (unique)

### MemoriesRepository (Qdrant: `memories`, 768-dim cosine)
- `save(user_id, text, metadata=None, created_at=None)` → point_id (UUID)
- `search(user_id, query, limit=5)` → semantic similarity results
- `get_by_id(point_id)`
- `find_by_date_range(user_id, date_from=None, date_to=None)`
- `delete(point_id)`

## Timezone Flow

1. `_invoke_agent()` calls `_get_user_timezone(user_id)` → reads from UsersRepository
2. `_build_system_prompt(user_timezone)` injects current UTC time + timezone instructions
3. If timezone is unknown → system prompt tells agent to ask user for current time, determine IANA timezone, and call `set_user_timezone`
4. If timezone is known → system prompt tells agent to use it when converting relative times to UTC for tasks

## Payments & Subscription

- **Provider**: Telegram Stars (currency `XTR`), no external gateway
- **Plan**: Monthly, 2 Stars (configurable in `bot.py` constants)
- **Flow**: `/subscribe` → Stars invoice → pre-checkout approval → successful payment → `extend_subscription()` + transaction record
- **Stacking**: Re-subscribing while active adds 30 days on top of remaining time
- **Gate**: `bot_participation` checks `get_subscription_status()` before processing messages; inactive users get a `/subscribe` reminder
- **Task scheduler**: Not gated — due tasks always fire regardless of subscription status
- See `docs/payments.md` for full details

## Environment Variables

| Variable                          | Required | Default                     | Notes                                               |
|-----------------------------------|----------|-----------------------------|-----------------------------------------------------|
| `TELEGRAM_BOT_TOKEN`              | Yes      | —                           | From @BotFather                                     |
| `GOOGLE_API_KEY`                  | Yes      | —                           | Gemini API (LLM + embeddings)                       |
| `GOOGLE_GENAI_USE_VERTEXAI`       | No       | `False`                     | Standard GenAI API                                  |
| `MONGODB_URI`                     | Yes      | `mongodb://localhost:27017` | Tasks, users, checkpoints                           |
| `QDRANT_URL`                      | No       | `http://localhost:6333`     | Override to `http://qdrant:6333` in Docker          |
| `ASSISTANT_SESSIONS_DATABASE_URL` | No       | —                           | PostgreSQL (referenced but checkpoint uses MongoDB) |

## Local Development

**Always use the project venv** for running Python, tests, and scripts:

```bash
# Activate venv first (Windows)
venv\Scripts\activate
# or on Linux/macOS
source venv/bin/activate
```

All commands below assume the venv is active.

## Testing

```bash
python -m pytest src/tests/ -v          # all tests (Qdrant tests need running instance)
python -m pytest src/tests/agent/ -v    # tool + agent tests only (no external deps)
docker compose up qdrant -d             # start Qdrant for repository tests
```

- **conftest.py**: in-memory Qdrant (`:memory:`), `mongomock`, mocked vectorizer (deterministic 768-dim vectors)
- Agent tests (`test_patron_agent.py`) are **skipped** — require real Gemini API
- 61 tests passing, 2 skipped

## Docker

```bash
docker compose up        # bot + qdrant
```

- Bot: Python 3.12-slim, `PYTHONPATH=/app:/app/src`, entry: `python src/bot.py`
- Qdrant: official image, ports 6333/6334, persistent volume `qdrant_data`

## CI/CD

`.github/workflows/ci.yml` — triggers on push to non-main branches:
- Python 3.12, `pip install -e .`, `pytest src/tests/ -v -s`
- Secret: `GEMINI_API_KEY`

## Design Patterns

- **DI**: `injector` library, all repos/services are singletons via `app_container`
- **Lazy tool loading**: tools cached globally, initialized on first agent call
- **State injection**: tools receive `user_id`/`chat_id` via LangGraph `InjectedState`
- **Separation**: Repositories (data) → Tools (agent interface) → Agent (orchestration) → Bot (Telegram)

## Project Config

- **Version**: 2.0.1 (`pyproject.toml`)
- **Python**: >= 3.12
- **Key deps**: `langchain~=1.2.12`, `langchain-google-genai`, `python-telegram-bot[job-queue]~=22.5`, `pymongo~=4.12`, `qdrant-client~=1.17.1`, `injector~=0.24`
- **Linting**: `flake8 src`
