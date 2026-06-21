"""
AstroGen — database.py
SQLite-based local storage OR PostgreSQL cloud database for session history and user data.
"""

import sqlite3
import os
import base64
from datetime import datetime
from pathlib import Path

DB_PATH  = os.path.join(os.path.dirname(__file__), '..', 'data', 'astrogen.db')
IMG_DIR  = os.path.join(os.path.dirname(__file__), '..', 'data', 'generated')

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)


def is_postgresql():
    return bool(os.getenv("DATABASE_URL"))


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            import psycopg2
            # Connect to PostgreSQL
            conn = psycopg2.connect(db_url)
            return conn
        except Exception as e:
            print(f"[DB] Error connecting to PostgreSQL: {e}. Falling back to SQLite.")
            
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def execute_query(conn, query, params=()):
    """Helper to abstract SQLite (?) and PostgreSQL (%s) placeholders."""
    is_pg = is_postgresql() and not isinstance(conn, sqlite3.Connection)
    if is_pg:
        query = query.replace('?', '%s')
    
    cur = conn.cursor()
    cur.execute(query, params)
    return cur


def fetch_all_dict(cur):
    """Helper to convert query result to list of dicts."""
    if hasattr(cur, 'description') and cur.description:
        columns = [col[0] for col in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
    return []


def fetch_one_dict(cur):
    """Helper to convert query result to single dict."""
    if hasattr(cur, 'description') and cur.description:
        row = cur.fetchone()
        if row:
            columns = [col[0] for col in cur.description]
            return dict(zip(columns, row))
    return None


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    cur  = conn.cursor()

    is_pg = is_postgresql() and not isinstance(conn, sqlite3.Connection)

    # Autoincrement style
    pk_type = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"

    # Sessions table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS sessions (
            id         {pk_type},
            title      TEXT    NOT NULL DEFAULT 'New Chat',
            created_at TEXT    NOT NULL,
            updated_at TEXT    NOT NULL
        )
    """)

    # Messages table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS messages (
            id          {pk_type},
            session_id  INTEGER NOT NULL,
            role        TEXT    NOT NULL,
            msg_type    TEXT    NOT NULL DEFAULT 'text',
            content     TEXT    NOT NULL,
            prompt      TEXT,
            model_used  TEXT,
            created_at  TEXT    NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)

    # Generated images catalog
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS generated_images (
            id          {pk_type},
            session_id  INTEGER,
            filename    TEXT    NOT NULL,
            filepath    TEXT    NOT NULL,
            prompt      TEXT,
            model_used  TEXT,
            width       INTEGER,
            height      INTEGER,
            created_at  TEXT    NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Initialized database (PostgreSQL={is_pg})")


# ── Session CRUD ────────────────────────────────────────────────────────────

def create_session(title: str = "New Chat") -> int:
    now  = datetime.now().isoformat()
    conn = get_conn()
    is_pg = is_postgresql() and not isinstance(conn, sqlite3.Connection)
    
    if is_pg:
        cur = execute_query(conn, "INSERT INTO sessions (title, created_at, updated_at) VALUES (?,?,?) RETURNING id", (title, now, now))
        session_id = cur.fetchone()[0]
    else:
        cur = execute_query(conn, "INSERT INTO sessions (title, created_at, updated_at) VALUES (?,?,?)", (title, now, now))
        session_id = cur.lastrowid
        
    conn.commit()
    conn.close()
    return session_id


def get_all_sessions() -> list:
    conn = get_conn()
    cur = execute_query(conn, """
        SELECT s.id, s.title, s.created_at, s.updated_at,
               COUNT(m.id) as message_count
        FROM sessions s
        LEFT JOIN messages m ON m.session_id = s.id
        GROUP BY s.id, s.title, s.created_at, s.updated_at
        ORDER BY s.updated_at DESC
    """)
    rows = fetch_all_dict(cur)
    conn.close()
    return rows


def rename_session(session_id: int, new_title: str):
    conn = get_conn()
    execute_query(conn, "UPDATE sessions SET title=?, updated_at=? WHERE id=?",
                 (new_title, datetime.now().isoformat(), session_id))
    conn.commit()
    conn.close()


def delete_session(session_id: int):
    conn = get_conn()
    execute_query(conn, "DELETE FROM messages WHERE session_id=?", (session_id,))
    execute_query(conn, "DELETE FROM sessions WHERE id=?", (session_id,))
    conn.commit()
    conn.close()


# ── Message CRUD ────────────────────────────────────────────────────────────

def add_message(session_id: int, role: str, content: str,
                msg_type: str = 'text', prompt: str = None,
                model_used: str = None) -> int:
    now  = datetime.now().isoformat()
    conn = get_conn()
    is_pg = is_postgresql() and not isinstance(conn, sqlite3.Connection)
    
    if is_pg:
        cur = execute_query(conn, """
            INSERT INTO messages (session_id, role, msg_type, content, prompt, model_used, created_at)
            VALUES (?,?,?,?,?,?,?) RETURNING id
        """, (session_id, role, msg_type, content, prompt, model_used, now))
        msg_id = cur.fetchone()[0]
    else:
        cur = execute_query(conn, """
            INSERT INTO messages (session_id, role, msg_type, content, prompt, model_used, created_at)
            VALUES (?,?,?,?,?,?,?)
        """, (session_id, role, msg_type, content, prompt, model_used, now))
        msg_id = cur.lastrowid
        
    # Update session updated_at
    execute_query(conn, "UPDATE sessions SET updated_at=? WHERE id=?", (now, session_id))
    conn.commit()
    conn.close()
    return msg_id


def get_session_messages(session_id: int) -> list:
    conn = get_conn()
    cur = execute_query(conn, """
        SELECT * FROM messages WHERE session_id=? ORDER BY created_at ASC
    """, (session_id,))
    rows = fetch_all_dict(cur)
    conn.close()
    return rows


def get_session_context(session_id: int, max_messages: int = 10) -> list:
    """Get recent messages for LLM context (text only)."""
    messages = get_session_messages(session_id)
    text_msgs = [m for m in messages if m['msg_type'] == 'text'][-max_messages:]
    return [{'role': m['role'], 'content': m['content']} for m in text_msgs]


# ── Image Storage ───────────────────────────────────────────────────────────

def save_generated_image(img_bytes: bytes, prompt: str, model_used: str,
                         session_id: int = None) -> dict:
    """Save generated image to disk and catalog in DB."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    filename  = f"gen_{model_used}_{timestamp}.png"
    filepath  = os.path.join(IMG_DIR, filename)

    with open(filepath, 'wb') as f:
        f.write(img_bytes)

    conn = get_conn()
    is_pg = is_postgresql() and not isinstance(conn, sqlite3.Connection)
    
    if is_pg:
        cur = execute_query(conn, """
            INSERT INTO generated_images (session_id, filename, filepath, prompt, model_used, created_at)
            VALUES (?,?,?,?,?,?) RETURNING id
        """, (session_id, filename, filepath, prompt, model_used, datetime.now().isoformat()))
        img_id = cur.fetchone()[0]
    else:
        cur = execute_query(conn, """
            INSERT INTO generated_images (session_id, filename, filepath, prompt, model_used, created_at)
            VALUES (?,?,?,?,?,?)
        """, (session_id, filename, filepath, prompt, model_used, datetime.now().isoformat()))
        img_id = cur.lastrowid
        
    conn.commit()
    conn.close()

    return {'id': img_id, 'filename': filename, 'filepath': filepath}


def get_all_generated_images(limit: int = 50) -> list:
    conn = get_conn()
    cur = execute_query(conn, """
        SELECT * FROM generated_images ORDER BY created_at DESC LIMIT ?
    """, (limit,))
    rows = fetch_all_dict(cur)
    conn.close()
    return rows


def image_to_base64(filepath: str) -> str:
    """Convert saved image to base64 for API response."""
    if not os.path.exists(filepath):
        return ''
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


# Initialize on import
init_db()
