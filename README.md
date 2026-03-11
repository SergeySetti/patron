# Patron

Patron is an agentic AI assistant for Telegram designed to help you plan, remember, and manage your daily life. It acts as a personal planning assistant that tracks tasks, goals, and schedules reminders for recurrent events.

## Purpose

The project is a prototype for a Telegram bot that serves as a planning and remembering personal assistant. It aims to:
- Remember what needs to be remembered.
- Schedule reminders.
- Manage recurrent events, tasks, goals, and plans.

*Note: This project is currently in its early prototype stage and is also intended for educational purposes, specifically exploring the use of LangChain as an agentic framework.*

## Features

- **Personal Assistant:** A unified interface to capture and recall information.
- **Task & Goal Management:** Track your short-term tasks and long-term goals.
- **Intelligent Scheduling:** Automated reminders and support for recurrent events.
- **Agentic AI:** Powered by LangChain and Google Gemini for natural language understanding and tool usage.

## Tech Stack

- **Framework:** [LangChain](https://www.langchain.com/)
- **AI Model:** Google Gemini (via `langchain-google-genai`)
- **Database:** MongoDB (via `pymongo`)
- **Telegram Interface:** [python-telegram-bot](https://python-telegram-bot.org/)
- **Dependency Injection:** `injector`

## Getting Started

### Prerequisites

- Python 3.12+
- MongoDB
- Telegram Bot Token (obtainable from [@BotFather](https://t.me/BotFather))
- Google AI API Key (for Gemini)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SergeySetti/patron.git
   cd patron
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e .
   ```

4. **Environment Configuration:**
   Create a `.env` file in the root directory and add your credentials:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   GOOGLE_API_KEY=your_google_api_key
   MONGODB_URI=your_mongodb_uri
   ```

## Development

### Running Tests

The project uses `pytest` for testing. You can run the tests using:

```bash
pytest
```

## License

This project is licensed under the terms of the license found in the repository (if applicable).
