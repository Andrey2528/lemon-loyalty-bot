import asyncio
import os
import logging
from typing import List, Tuple, Optional

# Імпортуємо базу даних модуль
try:
    # Спробуємо asyncpg для Supabase
    import asyncpg
    DATABASE_URL = os.getenv("DATABASE_URL")
    USE_SUPABASE = DATABASE_URL is not None
except ImportError:
    # Fallback до SQLite
    import sqlite3
    USE_SUPABASE = False

logger = logging.getLogger(__name__)

# Global connection pool for PostgreSQL
_pool = None

async def _init_postgres():
    """Initialize PostgreSQL connection"""
    global _pool
    if DATABASE_URL and not _pool:
        try:
            _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
            logger.info("PostgreSQL connection pool created")
            
            # Create tables
            async with _pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        phone VARCHAR(20),
                        bonus_points INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS promos (
                        id SERIAL PRIMARY KEY,
                        text TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
        except Exception as e:
            logger.error(f"PostgreSQL initialization failed: {e}")
            raise

def _init_sqlite():
    """Initialize SQLite database"""
    conn = sqlite3.connect("loyalty.db")
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            phone TEXT,
            bonus_points INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS promos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("SQLite database initialized")

def init_db():
    """Initialize database"""
    if USE_SUPABASE:
        asyncio.create_task(_init_postgres())
    else:
        _init_sqlite()
        logger.warning("Using SQLite fallback - data will not persist on cloud platforms")

def init_promos_table():
    """Initialize promos table"""
    pass  # Already handled in init_db

async def _add_user_postgres(user_id: int, phone: str, bonus_points: int = 0):
    """Add user to PostgreSQL"""
    async with _pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, phone, bonus_points) 
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) 
            DO UPDATE SET phone = EXCLUDED.phone, bonus_points = EXCLUDED.bonus_points
        """, user_id, phone, bonus_points)

def _add_user_sqlite(user_id: int, phone: str, bonus_points: int = 0):
    """Add user to SQLite"""
    conn = sqlite3.connect("loyalty.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO users (user_id, phone, bonus_points) 
        VALUES (?, ?, ?)
    """, (user_id, phone, bonus_points))
    conn.commit()
    conn.close()

def add_user(user_id: int, phone: str, bonus_points: int = 0):
    """Add user (sync wrapper)"""
    if USE_SUPABASE and _pool:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_add_user_postgres(user_id, phone, bonus_points))
        finally:
            loop.close()
    else:
        _add_user_sqlite(user_id, phone, bonus_points)

async def _get_user_postgres(user_id: int) -> Optional[Tuple[str, int]]:
    """Get user from PostgreSQL"""
    async with _pool.acquire() as conn:
        row = await conn.fetchrow("SELECT phone, bonus_points FROM users WHERE user_id = $1", user_id)
        if row:
            return (row['phone'], row['bonus_points'])
        return None

def _get_user_sqlite(user_id: int) -> Optional[Tuple[str, int]]:
    """Get user from SQLite"""
    conn = sqlite3.connect("loyalty.db")
    cur = conn.cursor()
    cur.execute("SELECT phone, bonus_points FROM users WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result

def get_user(user_id: int) -> Optional[Tuple[str, int]]:
    """Get user (sync wrapper)"""
    if USE_SUPABASE and _pool:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_get_user_postgres(user_id))
        finally:
            loop.close()
    else:
        return _get_user_sqlite(user_id)

async def _get_all_users_postgres() -> List[Tuple[int, str, int]]:
    """Get all users from PostgreSQL"""
    async with _pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id, phone, bonus_points FROM users")
        return [(row['user_id'], row['phone'], row['bonus_points']) for row in rows]

def _get_all_users_sqlite() -> List[Tuple[int, str, int]]:
    """Get all users from SQLite"""
    conn = sqlite3.connect("loyalty.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id, phone, bonus_points FROM users")
    result = cur.fetchall()
    conn.close()
    return result

def get_all_users() -> List[Tuple[int, str, int]]:
    """Get all users (sync wrapper)"""
    if USE_SUPABASE and _pool:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_get_all_users_postgres())
        finally:
            loop.close()
    else:
        return _get_all_users_sqlite()

async def _get_promos_postgres() -> List[Tuple[int, str]]:
    """Get promos from PostgreSQL"""
    async with _pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, text FROM promos ORDER BY id")
        return [(row['id'], row['text']) for row in rows]

def _get_promos_sqlite() -> List[Tuple[int, str]]:
    """Get promos from SQLite"""
    conn = sqlite3.connect("loyalty.db")
    cur = conn.cursor()
    cur.execute("SELECT id, text FROM promos ORDER BY id")
    result = cur.fetchall()
    conn.close()
    return result

def get_promos() -> List[Tuple[int, str]]:
    """Get promos (sync wrapper)"""
    if USE_SUPABASE and _pool:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_get_promos_postgres())
        finally:
            loop.close()
    else:
        return _get_promos_sqlite()

async def _add_promo_postgres(text: str):
    """Add promo to PostgreSQL"""
    async with _pool.acquire() as conn:
        await conn.execute("INSERT INTO promos (text) VALUES ($1)", text)

def _add_promo_sqlite(text: str):
    """Add promo to SQLite"""
    conn = sqlite3.connect("loyalty.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO promos (text) VALUES (?)", (text,))
    conn.commit()
    conn.close()

def add_promo(text: str):
    """Add promo (sync wrapper)"""
    if USE_SUPABASE and _pool:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_add_promo_postgres(text))
        finally:
            loop.close()
    else:
        _add_promo_sqlite(text)

async def _delete_promo_postgres(promo_id: int):
    """Delete promo from PostgreSQL"""
    async with _pool.acquire() as conn:
        await conn.execute("DELETE FROM promos WHERE id = $1", promo_id)

def _delete_promo_sqlite(promo_id: int):
    """Delete promo from SQLite"""
    conn = sqlite3.connect("loyalty.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM promos WHERE id = ?", (promo_id,))
    conn.commit()
    conn.close()

def delete_promo(promo_id: int):
    """Delete promo (sync wrapper)"""
    if USE_SUPABASE and _pool:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_delete_promo_postgres(promo_id))
        finally:
            loop.close()
    else:
        _delete_promo_sqlite(promo_id)

async def _clear_promos_postgres():
    """Clear all promos from PostgreSQL"""
    async with _pool.acquire() as conn:
        await conn.execute("DELETE FROM promos")

def _clear_promos_sqlite():
    """Clear all promos from SQLite"""
    conn = sqlite3.connect("loyalty.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM promos")
    conn.commit()
    conn.close()

def clear_promos():
    """Clear all promos (sync wrapper)"""
    if USE_SUPABASE and _pool:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_clear_promos_postgres())
        finally:
            loop.close()
    else:
        _clear_promos_sqlite()
