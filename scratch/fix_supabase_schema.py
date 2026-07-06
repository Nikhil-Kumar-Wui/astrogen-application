import os
import psycopg2

db_url = "postgresql://postgres:Sr%2553rj2%23DQvcfg@db.vudjkrauybcsaxetmtgn.supabase.co:5432/postgres"

print("Connecting to Supabase PG to fix schema...")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# 1. Create login_history table
try:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS login_history (
            id          SERIAL PRIMARY KEY,
            email       VARCHAR(255) NOT NULL,
            login_time  TEXT NOT NULL,
            ip_address  VARCHAR(255)
        )
    """)
    conn.commit()
    print("login_history table verified/created.")
except Exception as e:
    print("Error creating login_history table:", e)
    conn.rollback()

# 2. Add columns to users table
columns = [
    ("use_count", "INTEGER DEFAULT 0"),
    ("last_login", "TEXT"),
    ("last_reminder_sent", "VARCHAR(255)"),
    ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
]

for col_name, col_type in columns:
    try:
        cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};")
        conn.commit()
        print(f"Column {col_name} successfully added.")
    except Exception as e:
        print(f"Column {col_name} alter skipped/already exists: {e}")
        conn.rollback()

conn.close()
print("Supabase PG schema sync complete!")
