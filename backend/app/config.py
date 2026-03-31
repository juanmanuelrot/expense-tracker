from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = ""

    # AI APIs
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://expense:expense@localhost:5432/expense_tracker"

    # App defaults
    default_currency: str = "UYU"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
