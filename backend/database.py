"""
AstroGen — database.py
SQLite-based local storage for chat history and generated images.
No server needed. Stored at app/data/astrogen.db
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


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    cur  = conn.cursor()

    # Sessions table — each conversation is a session
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT    NOT NULL DEFAULT 'New Chat',
            created_at TEXT    NOT NULL,
            updated_at TEXT    NOT NULL
        )
    """)

    # Messages table — each message in a session
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL,
            role        TEXT    NOT NULL,   -- 'user' or 'assistant'
            msg_type    TEXT    NOT NULL DEFAULT 'text',  -- 'text' | 'image' | 'caption'
            content     TEXT    NOT NULL,   -- text content or image path
            prompt      TEXT,              -- original user prompt (for images)
            model_used  TEXT,              -- 'lora_sd' | 'vae_gan' | 'blip2' | 'gemini'
            created_at  TEXT    NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    # Generated images catalog
    cur.execute("""
        CREATE TABLE IF NOT EXISTS generated_images (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
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
    print(f"[DB] Initialized at {DB_PATH}")


# ── Session CRUD ────────────────────────────────────────────────────────────

def create_session(title: str = "New Chat") -> int:
    now  = datetime.now().isoformat()
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("INSERT INTO sessions (title, created_at, updated_at) VALUES (?,?,?)",
                (title, now, now))
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return session_id


def get_all_sessions() -> list:
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT s.id, s.title, s.created_at, s.updated_at,
               COUNT(m.id) as message_count
        FROM sessions s
        LEFT JOIN messages m ON m.session_id = s.id
        GROUP BY s.id
        ORDER BY s.updated_at DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def rename_session(session_id: int, new_title: str):
    conn = get_conn()
    conn.execute("UPDATE sessions SET title=?, updated_at=? WHERE id=?",
                 (new_title, datetime.now().isoformat(), session_id))
    conn.commit()
    conn.close()


def delete_session(session_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
    conn.commit()
    conn.close()


# ── Message CRUD ────────────────────────────────────────────────────────────

def add_message(session_id: int, role: str, content: str,
                msg_type: str = 'text', prompt: str = None,
                model_used: str = None) -> int:
    now  = datetime.now().isoformat()
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO messages (session_id, role, msg_type, content, prompt, model_used, created_at)
        VALUES (?,?,?,?,?,?,?)
    """, (session_id, role, msg_type, content, prompt, model_used, now))
    msg_id = cur.lastrowid
    # Update session updated_at
    conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (now, session_id))
    conn.commit()
    conn.close()
    return msg_id


def get_session_messages(session_id: int) -> list:
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT * FROM messages WHERE session_id=? ORDER BY created_at ASC
    """, (session_id,))
    rows = [dict(r) for r in cur.fetchall()]
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
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO generated_images (session_id, filename, filepath, prompt, model_used, created_at)
        VALUES (?,?,?,?,?,?)
    """, (session_id, filename, filepath, prompt, model_used, datetime.now().isoformat()))
    img_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {'id': img_id, 'filename': filename, 'filepath': filepath}


def get_all_generated_images(limit: int = 50) -> list:
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT * FROM generated_images ORDER BY created_at DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
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
