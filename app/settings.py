import os
from pydantic import BaseModel

class Settings(BaseModel):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change_me")
    PAYSTACK_SECRET_KEY: str = os.getenv("PAYSTACK_SECRET_KEY", "")
    COMMISSION_RATE: float = float(os.getenv("COMMISSION_RATE", "0.20"))
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "db.sqlite3")
    BASE_WEBAPP_URL: str = os.getenv("BASE_WEBAPP_URL", "")
    PLATFORM_NAME: str = os.getenv("PLATFORM_NAME", "Ghana Online Market")
    ADMIN_TELEGRAM_IDS: str = os.getenv("ADMIN_TELEGRAM_IDS", "")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

settings = Settings()
