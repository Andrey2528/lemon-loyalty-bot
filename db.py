import os
import logging
from typing import List, Tuple, Optional
import threading

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Import both database modules
import sqlite3  # Always available

if DATABASE_URL:
    # PostgreSQL with psycopg2
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        USE_POSTGRES = True
        logger.info("Using PostgreSQL database")
    except ImportError:
        logger.error("psycopg2 not found, falling back to SQLite")
        USE_POSTGRES = False
else:
    # SQLite fallback
    USE_POSTGRES = False
    logger.info("Using SQLite database")

# Thread-local storage for connections
_local = threading.local()

def get_connection():
    """Get database connection (thread-safe)"""
    global USE_POSTGRES
    
    if not hasattr(_local, 'connection') or _local.connection is None:
        if USE_POSTGRES and DATABASE_URL:
            try:
                _local.connection = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
                logger.info("Connected to PostgreSQL successfully")
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                logger.info("Falling back to SQLite")
                USE_POSTGRES = False
                _local.connection = sqlite3.connect("loyalty.db")
        else:
            _local.connection = sqlite3.connect("loyalty.db")
    return _local.connection

def close_connection():
    """Close database connection"""
    if hasattr(_local, 'connection') and _local.connection:
        _local.connection.close()
        _local.connection = None

def init_db():
    """Initialize database tables"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            # PostgreSQL syntax
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    phone VARCHAR(20),
                    bonus_points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # SQLite syntax
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    phone TEXT,
                    bonus_points INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        conn.commit()
        logger.info("Users table initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing users table: {e}")
    finally:
        if not USE_POSTGRES:  # SQLite connections should be closed
            close_connection()

def init_promos_table():
    """Initialize promos table"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            # PostgreSQL syntax
            cur.execute("""
                CREATE TABLE IF NOT EXISTS promos (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # SQLite syntax
            cur.execute("""
                CREATE TABLE IF NOT EXISTS promos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        conn.commit()
        logger.info("Promos table initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing promos table: {e}")
    finally:
        if not USE_POSTGRES:  # SQLite connections should be closed
            close_connection()

def add_user(user_id: int, phone: str, bonus_points: int = 0):
    """Add or update user"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO users (user_id, phone, bonus_points) 
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) 
                DO UPDATE SET phone = EXCLUDED.phone, bonus_points = EXCLUDED.bonus_points
            """, (user_id, phone, bonus_points))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO users (user_id, phone, bonus_points) 
                VALUES (?, ?, ?)
            """, (user_id, phone, bonus_points))
        
        conn.commit()
        logger.info(f"User {user_id} added/updated successfully")
        
    except Exception as e:
        logger.error(f"Error adding user: {e}")
    finally:
        if not USE_POSTGRES:
            close_connection()

def get_user(user_id: int) -> Optional[Tuple[str, int]]:
    """Get user by ID"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("SELECT phone, bonus_points FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if row:
                return (row['phone'], row['bonus_points'])
        else:
            cur.execute("SELECT phone, bonus_points FROM users WHERE user_id = ?", (user_id,))
            result = cur.fetchone()
            return result
            
        return None
        
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None
    finally:
        if not USE_POSTGRES:
            close_connection()

def get_all_users() -> List[Tuple[int, str, int]]:
    """Get all users"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("SELECT user_id, phone, bonus_points FROM users ORDER BY created_at")
            rows = cur.fetchall()
            return [(row['user_id'], row['phone'], row['bonus_points']) for row in rows]
        else:
            cur.execute("SELECT user_id, phone, bonus_points FROM users ORDER BY created_at")
            return cur.fetchall()
            
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []
    finally:
        if not USE_POSTGRES:
            close_connection()

def get_promos() -> List[Tuple[int, str]]:
    """Get all promos"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("SELECT id, text FROM promos ORDER BY id")
            rows = cur.fetchall()
            return [(row['id'], row['text']) for row in rows]
        else:
            cur.execute("SELECT id, text FROM promos ORDER BY id")
            return cur.fetchall()
            
    except Exception as e:
        logger.error(f"Error getting promos: {e}")
        return []
    finally:
        if not USE_POSTGRES:
            close_connection()

def add_promo(text: str):
    """Add promo"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("INSERT INTO promos (text) VALUES (%s)", (text,))
        else:
            cur.execute("INSERT INTO promos (text) VALUES (?)", (text,))
        
        conn.commit()
        logger.info("Promo added successfully")
        
    except Exception as e:
        logger.error(f"Error adding promo: {e}")
    finally:
        if not USE_POSTGRES:
            close_connection()

def delete_promo(promo_id: int):
    """Delete promo"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("DELETE FROM promos WHERE id = %s", (promo_id,))
        else:
            cur.execute("DELETE FROM promos WHERE id = ?", (promo_id,))
        
        conn.commit()
        logger.info(f"Promo {promo_id} deleted successfully")
        
    except Exception as e:
        logger.error(f"Error deleting promo: {e}")
    finally:
        if not USE_POSTGRES:
            close_connection()

def clear_promos():
    """Clear all promos"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM promos")
        conn.commit()
        logger.info("All promos cleared successfully")
        
    except Exception as e:
        logger.error(f"Error clearing promos: {e}")
    finally:
        if not USE_POSTGRES:
            close_connection()

def update_promo(promo_id: int, text: str):
    """Update promo text"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("UPDATE promos SET text = %s WHERE id = %s", (text, promo_id))
        else:
            cur.execute("UPDATE promos SET text = ? WHERE id = ?", (text, promo_id))
        
        conn.commit()
        logger.info(f"Promo {promo_id} updated successfully")
        
    except Exception as e:
        logger.error(f"Error updating promo: {e}")
    finally:
        if not USE_POSTGRES:
            close_connection()

def init_weekly_broadcast_table():
    """Initialize weekly broadcast table"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            # PostgreSQL syntax
            cur.execute("""
                CREATE TABLE IF NOT EXISTS weekly_broadcast (
                    id SERIAL PRIMARY KEY,
                    text TEXT,
                    day_of_week INTEGER DEFAULT 1,
                    hour INTEGER DEFAULT 10,
                    minute INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # SQLite syntax
            cur.execute("""
                CREATE TABLE IF NOT EXISTS weekly_broadcast (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT,
                    day_of_week INTEGER DEFAULT 1,
                    hour INTEGER DEFAULT 10,
                    minute INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        conn.commit()
        logger.info("Weekly broadcast table initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing weekly broadcast table: {e}")
    finally:
        if not USE_POSTGRES:
            close_connection()

def set_weekly_broadcast(text: str):
    """Set weekly broadcast text"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO weekly_broadcast (id, text) VALUES (1, %s)
                ON CONFLICT (id) DO UPDATE SET text = EXCLUDED.text
            """, (text,))
        else:
            cur.execute("INSERT OR REPLACE INTO weekly_broadcast (id, text) VALUES (1, ?)", (text,))
        
        conn.commit()
        logger.info("Weekly broadcast text set successfully")
        
    except Exception as e:
        logger.error(f"Error setting weekly broadcast: {e}")
    finally:
        if not USE_POSTGRES:
            close_connection()

def get_weekly_broadcast() -> Optional[str]:
    """Get weekly broadcast text"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("SELECT text FROM weekly_broadcast WHERE id = %s", (1,))
            row = cur.fetchone()
            if row:
                return row['text']
        else:
            cur.execute("SELECT text FROM weekly_broadcast WHERE id = ?", (1,))
            result = cur.fetchone()
            if result:
                return result[0]
            
        return None
        
    except Exception as e:
        logger.error(f"Error getting weekly broadcast: {e}")
        return None
    finally:
        if not USE_POSTGRES:
            close_connection()

def set_weekly_time(day: int, hour: int, minute: int):
    """Set weekly broadcast time"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO weekly_broadcast (id, day_of_week, hour, minute) VALUES (1, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    day_of_week = EXCLUDED.day_of_week,
                    hour = EXCLUDED.hour,
                    minute = EXCLUDED.minute
            """, (day, hour, minute))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO weekly_broadcast (id, day_of_week, hour, minute) 
                VALUES (1, ?, ?, ?)
            """, (day, hour, minute))
        
        conn.commit()
        logger.info(f"Weekly broadcast time set: day={day}, hour={hour}, minute={minute}")
        
    except Exception as e:
        logger.error(f"Error setting weekly time: {e}")
    finally:
        if not USE_POSTGRES:
            close_connection()

def get_weekly_time() -> Tuple[int, int, int]:
    """Get weekly broadcast time"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("SELECT day_of_week, hour, minute FROM weekly_broadcast WHERE id = %s", (1,))
            row = cur.fetchone()
            if row:
                return (row['day_of_week'], row['hour'], row['minute'])
        else:
            cur.execute("SELECT day_of_week, hour, minute FROM weekly_broadcast WHERE id = ?", (1,))
            result = cur.fetchone()
            if result:
                return result
                
        # Default values if no record found
        return (1, 10, 0)  # Monday, 10:00
        
    except Exception as e:
        logger.error(f"Error getting weekly time: {e}")
        return (1, 10, 0)  # Default values
    finally:
        if not USE_POSTGRES:
            close_connection()
