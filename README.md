# 🤖 Patron — Telegram Agentic AI Assistant

Patron is a Telegram bot that acts as a personal planning and remembering assistant. Built with LangChain and Google Gemini.

---

## 🛠️ Tech Stack

| Technology | Role |
|---|---|
| 🐍 **Python** >= 3.12 | Language |
| 🦜 **LangChain** | Agentic framework |
| ✨ **Google Gemini 3.1 Pro** | LLM |
| 💬 **python-telegram-bot** | Telegram integration |
| 🍃 **MongoDB** | Conversation state & user data persistence |
| 🔍 **Qdrant** | Vector database |
| 🐳 **Docker Compose** | Containerized deployment |

---

## 🚀 Getting Started

### 📋 Prerequisites

- 🐳 Docker & Docker Compose **or** 🐍 Python 3.12+
- 🔑 Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- 🔑 Google AI API Key
- 🍃 MongoDB instance

### 🔐 Environment Variables

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
GOOGLE_API_KEY=<your-google-api-key>
GOOGLE_GENAI_USE_VERTEXAI=False
MONGODB_URI=<your-mongodb-connection-string>
ASSISTANT_SESSIONS_DATABASE_URL=<your-postgresql-connection-string>
QDRANT_URL=http://localhost:6333
```

> **Docker Compose production note:** When both the bot and Qdrant run inside Docker Compose, set `QDRANT_URL=http://qdrant:6333` (the service name). This is already configured in `docker-compose.yml` via the `environment` block, so you do **not** need to add it to `.env` for production.

### 🐳 Run with Docker Compose

```bash
docker compose up
```

This starts the bot and a Qdrant instance (accessible at `http://localhost:6333`).

### 💻 Run Locally

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install .
python src/bot.py
```

---

## 🧪 Development

### ✅ Tests

```bash
python -m pytest src/tests/ -v
```

#### Running memories repository tests locally

The memories tests require a running Qdrant instance. Start only Qdrant via Docker Compose:

```bash
docker compose up qdrant -d
```

Then run the tests from your machine:

```bash
python -m pytest src/tests/repositories/ -v
```

Qdrant will be available at `http://localhost:6333`.

---

## 🧩 Features

### 🕐 Timezone-Aware Task Scheduling

Patron is timezone-aware when creating and managing tasks:

- **User timezone storage** — each user's IANA timezone (e.g. `Europe/Moscow`, `America/New_York`) is persisted in MongoDB via `UsersRepository`.
- **Automatic detection** — if the agent doesn't know a user's timezone, it asks for the current time, determines the IANA timezone, and saves it for future use.
- **UTC system clock** — the current UTC time is injected into the system prompt on every invocation, so the agent always knows "what time it is" and can convert relative times accurately.

### 🧠 Long-Term Memory

Patron stores and retrieves user memories in Qdrant, supporting semantic search and date-range filtering.

### 📋 Task Management

Create, list, and manage tasks through natural conversation. Tasks are stored in MongoDB with proper UTC timestamps derived from the user's timezone.

---

### 🔎 Linting

```bash
flake8 src
```
