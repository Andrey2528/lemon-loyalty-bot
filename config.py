import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is required")

DATABASE_URL = os.getenv("DATABASE_URL")  # Supabase PostgreSQL URL

ADMIN_USERNAMES = ["Andruh_a"]

#POSTER_TOKEN = "POSTER_API_KEY"
#POSTER_URL = "https://joinposter.com/api/"
