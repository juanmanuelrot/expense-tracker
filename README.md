# AI Expense Tracker

AI-powered expense tracker with a Telegram bot interface. Send text, photos of receipts, or voice messages — the AI extracts, categorizes, and records your expenses automatically.

## Features

- **Natural language input** — "Gasté $500 en el super con la débito del BROU"
- **Receipt scanning** — Send a photo and AI extracts all line items
- **Voice messages** — Speak your expense, AI transcribes and parses it
- **Multi-currency** — UYU and USD support (Uruguayan multi-currency accounts)
- **Account/card tracking** — Debit cards linked to bank accounts, standalone credit cards
- **Auto-categorization** — AI picks the right category (Food, Transport, Shopping, etc.)
- **Split expenses** — Track who owes you when paying for friends
- **Budgets** — Set monthly budgets per category with alerts
- **Bank statement reconciliation** — Upload CSV statements to cross-check

## Setup

### 1. Prerequisites

- Python 3.11+
- Docker (for PostgreSQL)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Anthropic API key
- OpenAI API key (for Whisper voice transcription)

### 2. Environment

```bash
cp .env.example .env
# Edit .env with your keys:
#   TELEGRAM_BOT_TOKEN=...
#   ANTHROPIC_API_KEY=...
#   OPENAI_API_KEY=...
```

### 3. Database

```bash
docker compose up -d          # Start PostgreSQL
cd backend
pip install -e .              # Install dependencies
alembic upgrade head          # Run migrations (creates tables + seeds categories)
```

### 4. Run the bot

```bash
cd backend
python -m bot.main
```

Then open Telegram, find your bot, and send `/start`.

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize your account |
| `/help` | Show all commands |
| `/accounts` | List bank accounts & cards |
| `/addaccount` | Add a bank account |
| `/addcard` | Add a debit/credit card |
| `/recent` | Last 10 expenses |
| `/summary` | Monthly spending by category |
| `/debts` | Who owes you money |
| `/settle <name>` | Mark debts as paid |
| `/setbudget <cat> <amount>` | Set category budget |
| `/budget` | View budget progress |

Plus: send any **text**, **photo**, or **voice message** to record an expense.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy 2.0, Alembic
- **Database:** PostgreSQL
- **Bot:** python-telegram-bot v21
- **AI:** Claude API (Anthropic) for NLP + Vision, Whisper (OpenAI) for voice
