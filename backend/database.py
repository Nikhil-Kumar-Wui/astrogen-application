"""
AstroGen — database.py
SQLite-based local storage OR PostgreSQL cloud database for session history and user data.
"""

import sqlite3
import os
import base64
from datetime import datetime
from pathlib import Path

import sys

PROJECT_ROOT = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSISTENT_DIR = os.path.join(os.getenv('APPDATA'), 'AstroGen') if (getattr(sys, 'frozen', False) and os.name == 'nt' and os.getenv('APPDATA')) else PROJECT_ROOT
os.makedirs(PERSISTENT_DIR, exist_ok=True)

from dotenv import load_dotenv
load_dotenv(os.path.join(PERSISTENT_DIR, '.env'))

def _get_db_path():
    if os.name == 'nt':
        appdata = os.getenv('APPDATA')
        if appdata:
            base_dir = os.path.join(appdata, 'AstroGen')
            os.makedirs(base_dir, exist_ok=True)
            return os.path.join(base_dir, 'astrogen.db')
    return os.path.join(PROJECT_ROOT, 'data', 'astrogen.db')

def _get_img_dir():
    target_dir = os.path.join(PERSISTENT_DIR, 'data', 'generated')
    os.makedirs(target_dir, exist_ok=True)
    return target_dir

DB_PATH  = _get_db_path()
IMG_DIR  = _get_img_dir()
ENC_DB_PATH = DB_PATH + ".enc"

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

# Keep-alive connection to keep the shared memory DB cache alive
_mem_keep_alive = sqlite3.connect("file:astrogen_mem?mode=memory&cache=shared", uri=True, check_same_thread=False)

# Decrypt database on startup and load it into shared memory
if os.path.exists(ENC_DB_PATH):
    try:
        from security import decrypt_file
        temp_db_path = DB_PATH + ".temp"
        decrypt_file(ENC_DB_PATH, temp_db_path)
        
        # Load from temp file and backup to shared memory
        disk_conn = sqlite3.connect(temp_db_path)
        disk_conn.backup(_mem_keep_alive)
        disk_conn.close()
        
        # Delete temp file
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        print("[DB] Loaded database into shared memory and deleted temp file.")
    except Exception as e:
        print(f"[DB] Error decrypting database on startup: {e}")

import atexit

def _cleanup_db():
    try:
        from security import encrypt_file
        temp_db_path = DB_PATH + ".temp"
        disk_conn = sqlite3.connect(temp_db_path)
        _mem_keep_alive.backup(disk_conn)
        disk_conn.close()
        
        encrypt_file(temp_db_path, ENC_DB_PATH)
        print("[DB] Saved shared memory database to encrypted disk file on exit.")
    except Exception as e:
        print(f"[DB] Error encrypting database on exit: {e}")

atexit.register(_cleanup_db)


import time
import threading

_pg_failed_until = 0.0
_db_lock = threading.Lock()

def is_postgresql():
    return bool(os.getenv("DATABASE_URL"))


def get_conn():
    global _pg_failed_until
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        now = time.time()
        if now < _pg_failed_until:
            # Cooldown active, skip trying PostgreSQL
            pass
        else:
            # Acquire lock in a non-blocking manner to prevent multiple concurrent connection attempts
            if _db_lock.acquire(blocking=False):
                try:
                    # Double check cooldown inside lock
                    if time.time() >= _pg_failed_until:
                        # Set a temporary cooldown immediately so other threads bypass this check
                        _pg_failed_until = time.time() + 60.0
                        import psycopg2
                        # Connect to PostgreSQL with 15 seconds timeout
                        conn = psycopg2.connect(db_url, connect_timeout=15)
                        # Reset cooldown on success
                        _pg_failed_until = 0.0
                        return conn
                except Exception as e:
                    print(f"[DB] Error connecting to PostgreSQL: {e}. Falling back to SQLite (cooldown 10m).")
                    _pg_failed_until = time.time() + 600.0  # 10 minutes cooldown
                finally:
                    _db_lock.release()
            
    conn = sqlite3.connect("file:astrogen_mem?mode=memory&cache=shared", uri=True, check_same_thread=False, timeout=30.0)
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
    """Create tables if they don't exist in both SQLite and PostgreSQL (if configured)."""
    # 1. Always initialize SQLite database tables
    try:
        sqlite_conn = sqlite3.connect("file:astrogen_mem?mode=memory&cache=shared", uri=True, check_same_thread=False, timeout=30.0)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cur = sqlite_conn.cursor()
        
        sqlite_cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL DEFAULT 'New Chat',
                created_at TEXT    NOT NULL,
                updated_at TEXT    NOT NULL,
                user_email TEXT
            )
        """)
        sqlite_cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL,
                role        TEXT    NOT NULL,
                msg_type    TEXT    NOT NULL DEFAULT 'text',
                content     TEXT    NOT NULL,
                prompt      TEXT,
                model_used  TEXT,
                created_at  TEXT    NOT NULL,
                user_email  TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        sqlite_cur.execute("""
            CREATE TABLE IF NOT EXISTS generated_images (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER,
                filename    TEXT    NOT NULL,
                filepath    TEXT    NOT NULL,
                prompt      TEXT,
                model_used  TEXT,
                width       INTEGER,
                height      INTEGER,
                created_at  TEXT    NOT NULL,
                user_email  TEXT
            )
        """)
        sqlite_cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email       TEXT UNIQUE NOT NULL,
                name        TEXT NOT NULL,
                picture     TEXT,
                created_at  TEXT NOT NULL,
                opt_in      INTEGER DEFAULT 0,
                purpose     TEXT,
                use_count   INTEGER DEFAULT 0,
                last_login  TEXT,
                last_reminder_sent TEXT
            )
        """)
        sqlite_cur.execute("""
            CREATE TABLE IF NOT EXISTS login_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email       TEXT NOT NULL,
                login_time  TEXT NOT NULL,
                ip_address  TEXT
            )
        """)
        
        # Upgrade columns for multi-user support and analytics
        for table in ['sessions', 'messages', 'generated_images']:
            try:
                sqlite_cur.execute(f"ALTER TABLE {table} ADD COLUMN user_email TEXT;")
            except Exception:
                pass
                
        for col in ['use_count INTEGER DEFAULT 0', 'last_login TEXT', 'last_reminder_sent TEXT']:
            try:
                sqlite_cur.execute(f"ALTER TABLE users ADD COLUMN {col};")
            except Exception:
                pass
                
        sqlite_conn.commit()
        sqlite_conn.close()
        print("[DB] Initialized local SQLite database tables successfully.")
    except Exception as e:
        print(f"[DB] Error initializing SQLite database tables: {e}")

    # 2. If PostgreSQL is configured, initialize PostgreSQL tables
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            import psycopg2
            pg_conn = psycopg2.connect(db_url, connect_timeout=15)
            pg_cur = pg_conn.cursor()
            
            pg_cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id         SERIAL PRIMARY KEY,
                    title      TEXT    NOT NULL DEFAULT 'New Chat',
                    created_at TEXT    NOT NULL,
                    updated_at TEXT    NOT NULL,
                    user_email VARCHAR(255)
                )
            """)
            pg_cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id          SERIAL PRIMARY KEY,
                    session_id  INTEGER NOT NULL,
                    role        TEXT    NOT NULL,
                    msg_type    TEXT    NOT NULL DEFAULT 'text',
                    content     TEXT    NOT NULL,
                    prompt      TEXT,
                    model_used  TEXT,
                    created_at  TEXT    NOT NULL,
                    user_email  VARCHAR(255),
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)
            pg_cur.execute("""
                CREATE TABLE IF NOT EXISTS generated_images (
                    id          SERIAL PRIMARY KEY,
                    session_id  INTEGER,
                    filename    TEXT    NOT NULL,
                    filepath    TEXT    NOT NULL,
                    prompt      TEXT,
                    model_used  TEXT,
                    width       INTEGER,
                    height      INTEGER,
                    created_at  TEXT    NOT NULL,
                    user_email  VARCHAR(255)
                )
            """)
            pg_cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id          SERIAL PRIMARY KEY,
                    email       VARCHAR(255) UNIQUE NOT NULL,
                    name        VARCHAR(255) NOT NULL,
                    picture     TEXT,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    opt_in      BOOLEAN DEFAULT FALSE,
                    purpose     VARCHAR(255),
                    use_count   INTEGER DEFAULT 0,
                    last_login  TEXT,
                    last_reminder_sent VARCHAR(255)
                )
            """)
            pg_cur.execute("""
                CREATE TABLE IF NOT EXISTS login_history (
                    id          SERIAL PRIMARY KEY,
                    email       VARCHAR(255) NOT NULL,
                    login_time  TEXT NOT NULL,
                    ip_address  VARCHAR(255)
                )
            """)
            
            # Upgrade columns for multi-user support and analytics
            for table in ['sessions', 'messages', 'generated_images']:
                try:
                    pg_cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS user_email VARCHAR(255);")
                    pg_conn.commit()
                except Exception as ex:
                    print(f"[DB] PG Alter {table} failed: {ex}")
                    pg_conn.rollback()
                    
            for col in ['use_count INTEGER DEFAULT 0', 'last_login TEXT', 'last_reminder_sent VARCHAR(255)']:
                try:
                    pg_cur.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col};")
                    pg_conn.commit()
                except Exception as ex:
                    print(f"[DB] PG Alter users column {col} failed: {ex}")
                    pg_conn.rollback()
                    
            pg_conn.close()
            print("[DB] Initialized remote PostgreSQL database tables successfully.")
            try:
                sync_local_to_cloud()
            except Exception as se:
                print(f"[DB] WARNING: Auto-sync failed on startup: {se}")
        except Exception as e:
            print(f"[DB] Could not initialize PostgreSQL on startup: {e}")



def get_current_user_email() -> str:
    """Helper to retrieve the current user's email, defaulting to guest."""
    env = read_env_local()
    state = read_state_local()
    email = env.get("USER_EMAIL") or state.get("user_email")
    if email:
        return email.strip()
    return "guest@astrogen.local"


# ── Session CRUD ────────────────────────────────────────────────────────────

def create_session(title: str = "New Chat") -> int:
    now  = datetime.now().isoformat()
    conn = get_conn()
    is_pg = is_postgresql() and not isinstance(conn, sqlite3.Connection)
    email = get_current_user_email()
    
    if is_pg:
        cur = execute_query(conn, "INSERT INTO sessions (title, created_at, updated_at, user_email) VALUES (?,?,?,?) RETURNING id", (title, now, now, email))
        session_id = cur.fetchone()[0]
    else:
        cur = execute_query(conn, "INSERT INTO sessions (title, created_at, updated_at, user_email) VALUES (?,?,?,?)", (title, now, now, email))
        session_id = cur.lastrowid
        
    conn.commit()
    conn.close()
    return session_id


def get_all_sessions() -> list:
    conn = get_conn()
    email = get_current_user_email()
    cur = execute_query(conn, """
        SELECT s.id, s.title, s.created_at, s.updated_at, s.user_email,
               COUNT(m.id) as message_count
        FROM sessions s
        LEFT JOIN messages m ON m.session_id = s.id
        WHERE s.user_email = ? OR (s.user_email IS NULL AND ? = 'guest@astrogen.local')
        GROUP BY s.id, s.title, s.created_at, s.updated_at, s.user_email
        ORDER BY s.updated_at DESC
    """, (email, email))
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
    email = get_current_user_email()
    
    if is_pg:
        cur = execute_query(conn, """
            INSERT INTO messages (session_id, role, msg_type, content, prompt, model_used, created_at, user_email)
            VALUES (?,?,?,?,?,?,?,?) RETURNING id
        """, (session_id, role, msg_type, content, prompt, model_used, now, email))
        msg_id = cur.fetchone()[0]
    else:
        cur = execute_query(conn, """
            INSERT INTO messages (session_id, role, msg_type, content, prompt, model_used, created_at, user_email)
            VALUES (?,?,?,?,?,?,?,?)
        """, (session_id, role, msg_type, content, prompt, model_used, now, email))
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
    
    # Resolve deduplicated image content if we hit a duplicate marker
    for row in rows:
        if row.get('msg_type') == 'image' and row.get('content') and row['content'].startswith('duplicate:msg_id:'):
            try:
                orig_id = int(row['content'].split(':')[-1])
                # Fetch original content from DB
                cur_orig = execute_query(conn, "SELECT content FROM messages WHERE id=?", (orig_id,))
                orig_row = fetch_one_dict(cur_orig)
                if orig_row and orig_row['content']:
                    row['content'] = orig_row['content']
            except Exception as e:
                print(f"[DB] Error resolving duplicate image message: {e}")
                
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
    email = get_current_user_email()
    
    if is_pg:
        cur = execute_query(conn, """
            INSERT INTO generated_images (session_id, filename, filepath, prompt, model_used, created_at, user_email)
            VALUES (?,?,?,?,?,?,?) RETURNING id
        """, (session_id, filename, filepath, prompt, model_used, datetime.now().isoformat(), email))
        img_id = cur.fetchone()[0]
    else:
        cur = execute_query(conn, """
            INSERT INTO generated_images (session_id, filename, filepath, prompt, model_used, created_at, user_email)
            VALUES (?,?,?,?,?,?,?)
        """, (session_id, filename, filepath, prompt, model_used, datetime.now().isoformat(), email))
        img_id = cur.lastrowid
        
    conn.commit()
    conn.close()

    return {'id': img_id, 'filename': filename, 'filepath': filepath}


def get_all_generated_images(limit: int = 50) -> list:
    conn = get_conn()
    email = get_current_user_email()
    cur = execute_query(conn, """
        SELECT * FROM generated_images 
        WHERE user_email = ? OR (user_email IS NULL AND ? = 'guest@astrogen.local')
        ORDER BY created_at DESC LIMIT ?
    """, (email, email, limit))
    rows = fetch_all_dict(cur)
    conn.close()
    return rows



def image_to_base64(filepath: str) -> str:
    """Convert saved image to base64 for API response."""
    if not os.path.exists(filepath):
        return ''
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def save_user_profile(email: str, name: str, picture: str, opt_in: bool = False, purpose: str = None):
    """Save user registration metadata directly to database."""
    conn = get_conn()
    try:
        is_pg = is_postgresql() and not isinstance(conn, sqlite3.Connection)
        if is_pg:
            execute_query(conn, """
                INSERT INTO users (email, name, picture, opt_in, purpose)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (email) DO UPDATE 
                SET name = EXCLUDED.name, picture = EXCLUDED.picture, opt_in = EXCLUDED.opt_in, purpose = EXCLUDED.purpose
            """, (email, name, picture, opt_in, purpose))
        else:
            now = datetime.now().isoformat()
            execute_query(conn, """
                INSERT INTO users (email, name, picture, created_at, opt_in, purpose)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (email) DO UPDATE 
                SET name = EXCLUDED.name, picture = EXCLUDED.picture, opt_in = EXCLUDED.opt_in, purpose = EXCLUDED.purpose
            """, (email, name, picture, now, 1 if opt_in else 0, purpose))
        conn.commit()
        print(f"[DB] Successfully saved user profile to database: {email}")
    except Exception as e:
        print(f"[DB] Error saving user profile: {e}")
    finally:
        conn.close()


def read_env_local():
    """Local helper to read .env without circular imports."""
    env_path = os.path.join(PERSISTENT_DIR, '.env')
    env = {}
    try:
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        k, _, v = line.partition('=')
                        env[k.strip()] = v.strip().strip("'\"")
    except Exception:
        pass
    return env

def read_state_local():
    """Local helper to read app_state.json without circular imports."""
    state_path = os.path.join(PERSISTENT_DIR, 'data', 'app_state.json')
    default = {"launch_count": 0, "kaggle_connected": False, "kaggle_url": ""}
    try:
        if os.path.exists(state_path):
            import json
            with open(state_path, 'r', encoding='utf-8') as f:
                return {**default, **json.load(f)}
    except Exception:
        pass
    return default

_image_sync_paused_until = 0.0
_image_sync_was_paused = False

def sync_local_to_cloud():
    """
    Synchronize missing local SQLite data (sessions, messages, generated_images, users)
    to remote PostgreSQL (Supabase) when online.
    Also ensures active user profile is correctly populated.
    """
    global _image_sync_paused_until, _image_sync_was_paused
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return
        
    print("[DB] Starting SQLite-to-Supabase synchronization check...")
    import psycopg2
    import shutil
    
    # Check local storage space
    try:
        total, used, free = shutil.disk_usage(os.path.dirname(DB_PATH))
        # If free space is < 500MB, flag nearly full
        if free < 500 * 1024 * 1024:
            print(f"[DB] WARNING: Local storage is nearly full ({free / 1024 / 1024:.2f} MB free). Pausing image sync.")
            _image_sync_paused_until = time.time() + 600.0 # Pause for 10 minutes
            _image_sync_was_paused = True
    except Exception as se:
        print(f"[DB] Error checking local storage usage: {se}")

    try:
        # 1. Connect to both databases
        pg_conn = psycopg2.connect(db_url, connect_timeout=15)
        sl_conn = sqlite3.connect("file:astrogen_mem?mode=memory&cache=shared", uri=True, timeout=10.0)
        sl_conn.row_factory = sqlite3.Row
        
        sl_cur = sl_conn.cursor()
        pg_cur = pg_conn.cursor()

        # Check cloud image count
        try:
            pg_cur.execute("SELECT COUNT(*) FROM messages WHERE msg_type = 'image'")
            pg_img_msg_count = pg_cur.fetchone()[0]
            pg_cur.execute("SELECT COUNT(*) FROM generated_images")
            pg_gen_img_count = pg_cur.fetchone()[0]
            total_pg_imgs = pg_img_msg_count + pg_gen_img_count
            if total_pg_imgs >= 150:
                print(f"[DB] WARNING: Cloud database has {total_pg_imgs} images (limit 150). Pausing image sync.")
                _image_sync_paused_until = time.time() + 600.0
                _image_sync_was_paused = True
        except Exception as pge:
            print(f"[DB] Error checking remote image counts: {pge}")

        # 1.5 Sync active profile from app_state/env to local & cloud DB
        try:
            state = read_state_local()
            env = read_env_local()
            email = env.get("USER_EMAIL") or state.get("user_email")
            name = env.get("USER_NAME") or state.get("user_name")
            picture = env.get("USER_PICTURE") or state.get("user_picture")
            if email and name:
                now = datetime.now().isoformat()
                sl_cur.execute("""
                    INSERT INTO users (email, name, picture, created_at, opt_in, purpose)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT (email) DO UPDATE 
                    SET name = EXCLUDED.name, picture = EXCLUDED.picture
                """, (email, name, picture, now, 1, "AstroGen Studio"))
                sl_conn.commit()
                
                pg_cur.execute("""
                    INSERT INTO users (email, name, picture, opt_in, purpose)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (email) DO UPDATE 
                    SET name = EXCLUDED.name, picture = EXCLUDED.picture
                """, (email, name, picture, True, "AstroGen Studio"))
                pg_conn.commit()
                print(f"[DB] Synced active profile to local & cloud databases: {email}")
        except Exception as ue:
            print(f"[DB] WARNING: Failed to sync active profile to DB: {ue}")
        
        # 2. Sync sessions
        sl_cur.execute("SELECT * FROM sessions")
        local_sessions = sl_cur.fetchall()
        for sess in local_sessions:
            pg_cur.execute("SELECT id FROM sessions WHERE id = %s", (sess['id'],))
            if not pg_cur.fetchone():
                pg_cur.execute(
                    "INSERT INTO sessions (id, title, created_at, updated_at, user_email) VALUES (%s, %s, %s, %s, %s)",
                    (sess['id'], sess['title'], sess['created_at'], sess['updated_at'], sess['user_email'])
                )
            else:
                pg_cur.execute(
                    "UPDATE sessions SET title=%s, updated_at=%s, user_email=%s WHERE id=%s AND updated_at < %s",
                    (sess['title'], sess['updated_at'], sess['user_email'], sess['id'], sess['updated_at'])
                )
        # Update PG sequence
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('sessions', 'id'), coalesce(max(id), 0) + 1, false) FROM sessions")
        
        # Determine if image sync is allowed
        now_ts = time.time()
        image_sync_allowed = (now_ts >= _image_sync_paused_until)
        sync_limit = None
        if image_sync_allowed and _image_sync_was_paused:
            print("[DB] Storage check passed. Restarting image sync with a safety limit of 5 images per run.")
            sync_limit = 5
            
        synced_images_count = 0

        # 3. Sync messages (with automatic conversion of local image references to base64 & deduplication)
        sl_cur.execute("SELECT * FROM messages")
        local_messages = sl_cur.fetchall()
        for msg in local_messages:
            is_image = (msg['msg_type'] == 'image')
            if is_image and not image_sync_allowed:
                # Skip image messages during sync pause
                continue
            if is_image and sync_limit is not None and synced_images_count >= sync_limit:
                continue

            content_to_save = msg['content']
            
            # If it is an image and is a local file reference, convert to base64 for Supabase
            if is_image and content_to_save and not content_to_save.startswith('data:') and not content_to_save.startswith('duplicate:'):
                try:
                    fpath = content_to_save
                    if not os.path.isabs(fpath):
                        fpath = os.path.join(IMG_DIR, fpath)
                    
                    if os.path.exists(fpath):
                        with open(fpath, "rb") as imf:
                            b64_data = base64.b64encode(imf.read()).decode('utf-8')
                        content_to_save = f"data:image/png;base64,{b64_data}"
                        # Proactively update the local database content to base64 as well
                        sl_cur2 = sl_conn.cursor()
                        sl_cur2.execute("UPDATE messages SET content = ? WHERE id = ?", (content_to_save, msg['id']))
                        sl_conn.commit()
                except Exception as ie:
                    print(f"[DB] WARNING: Failed to convert local image to base64 for cloud sync: {ie}")

            # DEDUPLICATION: If image base64, check if it already exists in another message in PostgreSQL
            if is_image and content_to_save and content_to_save.startswith('data:'):
                pg_cur.execute("SELECT id FROM messages WHERE content = %s AND id != %s LIMIT 1", (content_to_save, msg['id']))
                dup_row = pg_cur.fetchone()
                if dup_row:
                    print(f"[DB] Deduplicating image message {msg['id']}. Referencing message {dup_row[0]}")
                    content_to_save = f"duplicate:msg_id:{dup_row[0]}"

            pg_cur.execute("SELECT id FROM messages WHERE id = %s", (msg['id'],))
            if not pg_cur.fetchone():
                pg_cur.execute(
                    "INSERT INTO messages (id, session_id, role, msg_type, content, prompt, model_used, created_at, user_email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (msg['id'], msg['session_id'], msg['role'], msg['msg_type'], content_to_save, msg['prompt'], msg['model_used'], msg['created_at'], msg['user_email'])
                )
                if is_image:
                    synced_images_count += 1
            else:
                pg_cur.execute(
                    "UPDATE messages SET user_email=%s WHERE id=%s",
                    (msg['user_email'], msg['id'])
                )
        # Update PG sequence
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('messages', 'id'), coalesce(max(id), 0) + 1, false) FROM messages")
        
        # 4. Sync generated_images
        sl_cur.execute("SELECT * FROM generated_images")
        local_images = sl_cur.fetchall()
        for img in local_images:
            if not image_sync_allowed:
                continue
            if sync_limit is not None and synced_images_count >= sync_limit:
                continue

            pg_cur.execute("SELECT id FROM generated_images WHERE id = %s", (img['id'],))
            if not pg_cur.fetchone():
                pg_cur.execute(
                    "INSERT INTO generated_images (id, session_id, filename, filepath, prompt, model_used, width, height, created_at, user_email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (img['id'], img['session_id'], img['filename'], img['filepath'], img['prompt'], img['model_used'], img['width'], img['height'], img['created_at'], img['user_email'])
                )
                synced_images_count += 1
            else:
                pg_cur.execute(
                    "UPDATE generated_images SET user_email=%s WHERE id=%s",
                    (img['user_email'], img['id'])
                )
        # Update PG sequence
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('generated_images', 'id'), coalesce(max(id), 0) + 1, false) FROM generated_images")
        
        # 4.5 Sync login_history
        sl_cur.execute("SELECT * FROM login_history")
        local_logins = sl_cur.fetchall()
        for log in local_logins:
            pg_cur.execute("SELECT id FROM login_history WHERE id = %s", (log['id'],))
            if not pg_cur.fetchone():
                pg_cur.execute(
                    "INSERT INTO login_history (id, email, login_time, ip_address) VALUES (%s, %s, %s, %s)",
                    (log['id'], log['email'], log['login_time'], log['ip_address'])
                )
        # Update PG sequence
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('login_history', 'id'), coalesce(max(id), 0) + 1, false) FROM login_history")
        
        # 5. Sync users
        sl_cur.execute("SELECT * FROM users")
        local_users = sl_cur.fetchall()
        for usr in local_users:
            usr_dict = dict(usr)
            pg_cur.execute("SELECT email FROM users WHERE email = %s", (usr_dict['email'],))
            if not pg_cur.fetchone():
                pg_cur.execute(
                    "INSERT INTO users (email, name, picture, created_at, opt_in, purpose, use_count, last_login, last_reminder_sent) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (usr_dict['email'], usr_dict['name'], usr_dict['picture'], usr_dict['created_at'], bool(usr_dict['opt_in']), usr_dict['purpose'], usr_dict.get('use_count', 0), usr_dict.get('last_login'), usr_dict.get('last_reminder_sent'))
                )
            else:
                pg_cur.execute(
                    "UPDATE users SET name=%s, picture=%s, use_count=%s, last_login=%s, last_reminder_sent=%s WHERE email=%s",
                    (usr_dict['name'], usr_dict['picture'], usr_dict.get('use_count', 0), usr_dict.get('last_login'), usr_dict.get('last_reminder_sent'), usr_dict['email'])
                )
        
        # If we successfully synced and was limited, but did not hit any new warnings, clear was_paused flag
        if sync_limit is not None and synced_images_count < sync_limit:
            _image_sync_was_paused = False

        pg_conn.commit()
        pg_conn.close()
        sl_conn.close()
        print("[DB] SQLite-to-Supabase synchronization completed successfully!")
    except Exception as e:
        print(f"[DB] WARNING: SQLite-to-Supabase sync failed: {e}")


def get_latest_user_profile() -> dict:
    """Retrieve the latest signed-in user details."""
    conn = get_conn()
    try:
        cur = execute_query(conn, "SELECT email, name, picture FROM users ORDER BY id DESC LIMIT 1")
        row = fetch_one_dict(cur)
        return row
    except Exception as e:
        print(f"[DB] Error getting user profile: {e}")
        return None
    finally:
        conn.close()


def record_login(email: str, ip_address: str):
    """Record login event in SQLite and PostgreSQL."""
    now = datetime.now().isoformat()
    conn = get_conn()
    try:
        is_pg = is_postgresql() and not isinstance(conn, sqlite3.Connection)
        if is_pg:
            pg_cur = conn.cursor()
            pg_cur.execute("""
                INSERT INTO login_history (email, login_time, ip_address)
                VALUES (%s, %s, %s)
            """, (email, now, ip_address))
        else:
            sl_cur = conn.cursor()
            sl_cur.execute("""
                INSERT INTO login_history (email, login_time, ip_address)
                VALUES (?, ?, ?)
            """, (email, now, ip_address))
        conn.commit()
        print(f"[DB] Recorded login for {email} from {ip_address}")
    except Exception as e:
        print(f"[DB] Error recording login: {e}")
    finally:
        conn.close()


def increment_user_use_count(email: str):
    """Increment use count for user and update last_login."""
    now = datetime.now().isoformat()
    conn = get_conn()
    try:
        is_pg = is_postgresql() and not isinstance(conn, sqlite3.Connection)
        if is_pg:
            pg_cur = conn.cursor()
            pg_cur.execute("""
                UPDATE users SET use_count = COALESCE(use_count, 0) + 1, last_login = %s WHERE email = %s
            """, (now, email))
        else:
            sl_cur = conn.cursor()
            sl_cur.execute("""
                UPDATE users SET use_count = COALESCE(use_count, 0) + 1, last_login = ? WHERE email = ?
            """, (now, email))
        conn.commit()
        print(f"[DB] Incremented use_count for user: {email}")
    except Exception as e:
        print(f"[DB] Error incrementing use count: {e}")
    finally:
        conn.close()


def check_and_send_inactivity_reminders():
    """Send monthly inactivity reminders to users who haven't logged in for 30 days."""
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    if not resend_key:
        print("[DB] RESEND_API_KEY not configured. Skipping inactivity reminders check.")
        return
        
    conn = get_conn()
    try:
        cur = execute_query(conn, "SELECT email, name, last_login, created_at, last_reminder_sent FROM users")
        users = fetch_all_dict(cur)
        now = datetime.now()
        
        for u in users:
            email = u['email']
            name = u['name']
            
            # Resolve last login or creation date
            last_login_str = u.get('last_login') or u.get('created_at')
            if not last_login_str:
                continue
                
            try:
                # Handle possible ISO format timestamps
                last_login_dt = datetime.fromisoformat(last_login_str.split('.')[0])
            except Exception:
                continue
                
            days_inactive = (now - last_login_dt).days
            if days_inactive >= 30:
                last_rem_sent_str = u.get('last_reminder_sent')
                should_send = True
                if last_rem_sent_str:
                    try:
                        last_rem_dt = datetime.fromisoformat(last_rem_sent_str.split('.')[0])
                        days_since_rem = (now - last_rem_dt).days
                        if days_since_rem < 30:
                            should_send = False
                    except Exception:
                        pass
                
                if should_send:
                    # Send monthly inactivity reminder email
                    import requests
                    url = "https://api.resend.com/emails"
                    headers = {
                        "Authorization": f"Bearer {resend_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "from": "AstroGen Space Studio <reminders@resend.dev>",
                        "to": [email],
                        "subject": "We miss you at AstroGen Space Studio!",
                        "html": f"""
                        <html>
                        <body style="font-family: sans-serif; background-color: #040508; color: #ffffff; padding: 30px; border-radius: 12px;">
                            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #1f2937; padding: 20px; border-radius: 8px; background-color: #080b18;">
                                <h2 style="color: #6366f1; border-bottom: 1px solid #1f2937; padding-bottom: 10px;">✦ ASTROGEN SPACE STUDIO</h2>
                                <p>Hello <strong>{name}</strong>,</p>
                                <p>It's been a while since you last explored the stars with AstroGen Space Studio!</p>
                                <p>We've added new enhancements, optimized image generation speed, and improved database syncing.</p>
                                <p>Launch the app to see what's new and continue generating your space art!</p>
                                <br>
                                <hr style="border: 0; border-top: 1px solid #1f2937;">
                                <p style="font-size: 11px; color: #64748b;">AstroGen Space Studio &bull; Monthly Reminder</p>
                            </div>
                        </body>
                        </html>
                        """
                    }
                    try:
                        r = requests.post(url, json=payload, headers=headers, timeout=10)
                        if r.status_code == 200 or r.status_code == 201:
                            print(f"[DB] Sent inactivity email to {email}")
                            # Update last_reminder_sent
                            now_iso = now.isoformat()
                            execute_query(conn, "UPDATE users SET last_reminder_sent = ? WHERE email = ?", (now_iso, email))
                            conn.commit()
                    except Exception as re_err:
                        print(f"[DB] Error sending inactivity reminder: {re_err}")
    except Exception as e:
        print(f"[DB] Error checking inactivity reminders: {e}")
    finally:
        conn.close()


def restore_user_data_from_cloud(email: str):
    """
    Download/Restore user data (sessions, messages, generated_images)
    from remote Supabase PostgreSQL to local SQLite database for the given email.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return
        
    print(f"[DB] Restoring data from Supabase for email: {email}...")
    import psycopg2
    try:
        pg_conn = psycopg2.connect(db_url, connect_timeout=5)
        sl_conn = sqlite3.connect("file:astrogen_mem?mode=memory&cache=shared", uri=True, timeout=15.0)
        sl_conn.row_factory = sqlite3.Row
        
        pg_cur = pg_conn.cursor()
        sl_cur = sl_conn.cursor()
        
        # 1. Fetch sessions from PG for this user
        pg_cur.execute("""
            SELECT id, title, created_at, updated_at, user_email 
            FROM sessions 
            WHERE user_email = %s
        """, (email,))
        sessions = pg_cur.fetchall()
        for sess in sessions:
            s_id, s_title, s_created, s_updated, s_email = sess
            sl_cur.execute("SELECT id FROM sessions WHERE id = ?", (s_id,))
            if not sl_cur.fetchone():
                sl_cur.execute("""
                    INSERT INTO sessions (id, title, created_at, updated_at, user_email)
                    VALUES (?, ?, ?, ?, ?)
                """, (s_id, s_title, s_created, s_updated, s_email))
        sl_conn.commit()

        # 2. Fetch messages from PG for this user
        pg_cur.execute("""
            SELECT id, session_id, role, msg_type, content, prompt, model_used, created_at, user_email 
            FROM messages 
            WHERE user_email = %s
        """, (email,))
        messages = pg_cur.fetchall()
        for msg in messages:
            m_id, m_sess_id, m_role, m_type, m_content, m_prompt, m_model, m_created, m_email = msg
            sl_cur.execute("SELECT id FROM messages WHERE id = ?", (m_id,))
            if not sl_cur.fetchone():
                sl_cur.execute("""
                    INSERT INTO messages (id, session_id, role, msg_type, content, prompt, model_used, created_at, user_email)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (m_id, m_sess_id, m_role, m_type, m_content, m_prompt, m_model, m_created, m_email))
        sl_conn.commit()

        # 3. Fetch generated_images from PG for this user
        pg_cur.execute("""
            SELECT id, session_id, filename, filepath, prompt, model_used, width, height, created_at, user_email 
            FROM generated_images 
            WHERE user_email = %s
        """, (email,))
        images = pg_cur.fetchall()
        for img in images:
            i_id, i_sess_id, i_filename, i_filepath, i_prompt, i_model, i_width, i_height, i_created, i_email = img
            sl_cur.execute("SELECT id FROM generated_images WHERE id = ?", (i_id,))
            if not sl_cur.fetchone():
                sl_cur.execute("""
                    INSERT INTO generated_images (id, session_id, filename, filepath, prompt, model_used, width, height, created_at, user_email)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (i_id, i_sess_id, i_filename, i_filepath, i_prompt, i_model, i_width, i_height, i_created, i_email))
        sl_conn.commit()
        
        pg_conn.close()
        sl_conn.close()
        print(f"[DB] Successfully restored user data from Supabase for {email}!")
    except Exception as e:
        print(f"[DB] Error restoring user data from Supabase: {e}")


# Initialize on import
init_db()
