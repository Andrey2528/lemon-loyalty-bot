import os
import logging

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is required")

DATABASE_URL = os.getenv("DATABASE_URL")  # Supabase PostgreSQL URL
if DATABASE_URL:
    # Приховуємо пароль в логах
    safe_url = DATABASE_URL[:50] + "..." if len(DATABASE_URL) > 50 else DATABASE_URL
    if ":" in safe_url and "@" in safe_url:
        parts = safe_url.split(":")
        if len(parts) >= 3:
            safe_url = f"{parts[0]}:{parts[1]}:***@{parts[-1].split('@')[-1]}"
    logger.info(f"DATABASE_URL configured: {safe_url}")
else:
    logger.info("DATABASE_URL not set, will use SQLite")

ADMIN_USERNAMES = ["Andruh_a"]

#POSTER_TOKEN = "POSTER_API_KEY"
#POSTER_URL = "https://joinposter.com/api/"
