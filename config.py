from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()
]
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./checklist.db")
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")
REPORT_CHAT_ID: int = int(os.getenv("REPORT_CHAT_ID", "0"))
WEBAPP_PORT: int = int(os.getenv("WEBAPP_PORT", "8080"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env")
