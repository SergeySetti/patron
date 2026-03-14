# Patron - Telegram Agentic AI Assistant

Patron is an intelligent Telegram bot designed as a personal planning and remembering assistant. It helps users manage their schedules, reminders, tasks, goals, and plans, ensuring that nothing important is forgotten.

## Purpose

The primary goal of Patron is to act as a reliable companion for managing personal organization. It can:
- Remember information for later recall.
- Schedule reminders and recurrent events.
- Track tasks, goals, and long-term plans.

For educational purposes, this project is built using the **LangChain** agentic framework, though it also explores integrations with Google's AI ecosystem.

## Features

- **Advanced AI Reasoning:** Powered by `gemini-3.1-pro-preview` via Google Generative AI.
- **Agentic Capabilities:** Built using LangChain's agent system, allowing the bot to use tools and make decisions autonomously.
- **Personal Organization:** Dedicated focus on reminders, tasks, and goal management.
- **Telegram Integration:** Easy-to-use interface via the Telegram messaging app.
- **Scalable Architecture:** Uses Dependency Injection with the `injector` library for a clean and maintainable codebase.
- **Persistence:** Integrated with MongoDB for storing user data, reminders, and session information.

## Tech Stack

- **Language:** Python >= 3.12
- **Frameworks:** [LangChain](https://www.langchain.com/), [python-telegram-bot](https://python-telegram-bot.org/)
- **AI Model:** Google Gemini 3.1 Pro
- **Database:** MongoDB (via `pymongo`)
- **Testing:** `pytest`

## Getting Started

### Prerequisites

- Python 3.12 or higher
- A Telegram Bot Token (obtained from [@BotFather](https://t.me/BotFather))
- A Google AI API Key (for Gemini)
- A MongoDB instance

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/SergeySetti/patron.git
   cd patron
   ```

2. Install dependencies:
   ```bash
   pip install .
   ```

3. Configure environment variables:
   Create a `.env` file in the root directory and add your credentials:
   - `TELEGRAM_TOKEN`
   - `GOOGLE_API_KEY`
   - `MONGO_URI`

### Running the Bot

To start the bot, run:
```bash
python -m bot
```

## Development

### Running Tests

```bash
python -m pytest src/tests/ -v 2>&1
```

### Linting

```bash
flake8 src
```

## License

This project is licensed under the terms specified in the repository.
