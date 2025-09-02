def init_promos_table():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS promos (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT)")
    conn.commit()
    conn.close()

def get_promos():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, text FROM promos ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows

def add_promo(text):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT INTO promos (text) VALUES (?)", (text,))
    conn.commit()
    conn.close()

def update_promo(promo_id, text):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE promos SET text=? WHERE id=?", (text, promo_id))
    conn.commit()
    conn.close()

def delete_promo(promo_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM promos WHERE id=?", (promo_id,))
    conn.commit()
    conn.close()
def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT tg_id FROM users")
    return cur.fetchall()
import sqlite3

DB_NAME = "loyalty.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        tg_id INTEGER PRIMARY KEY,
        phone TEXT,
        poster_id INTEGER
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS weekly_broadcast (
        id INTEGER PRIMARY KEY,
        text TEXT
    , day_of_week INTEGER DEFAULT 0
    , hour INTEGER DEFAULT 12
    , minute INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()
def get_weekly_broadcast():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT text FROM weekly_broadcast WHERE id=1")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def get_weekly_time():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT day_of_week, hour, minute FROM weekly_broadcast WHERE id=1")
    row = cur.fetchone()
    conn.close()
    if row:
        return row
    return (0, 12, 0)  # за замовчуванням неділя 12:00

def set_weekly_time(day_of_week, hour, minute):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO weekly_broadcast (id, day_of_week, hour, minute) VALUES (1, ?, ?, ?)", (day_of_week, hour, minute))
    conn.commit()
    conn.close()

def set_weekly_broadcast(text):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO weekly_broadcast (id, text) VALUES (1, ?)", (text,))
    conn.commit()
    conn.close()

def add_user(tg_id, phone, poster_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (tg_id, phone, poster_id))
    conn.commit()
    conn.close()

def get_user(tg_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT phone, poster_id FROM users WHERE tg_id=?", (tg_id,))
    return cur.fetchone()
