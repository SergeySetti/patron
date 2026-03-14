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
| 🍃 **MongoDB** | Conversation state persistence |
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
```

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

### 🔎 Linting

```bash
flake8 src
```
