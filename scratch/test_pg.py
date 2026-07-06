import psycopg2
import os
import sys

db_url = "postgresql://postgres:Sr%2553rj2%23DQvcfg@db.vudjkrauybcsaxetmtgn.supabase.co:5432/postgres"

print("Attempting to connect to Supabase PostgreSQL...")
try:
    conn = psycopg2.connect(db_url, connect_timeout=5)
    print("Success! Connection established.")
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print("Version:", cur.fetchone())
    cur.execute("SELECT * FROM users;")
    print("Users:", cur.fetchall())
    cur.close()
    conn.close()
except Exception as e:
    print("Error connecting:")
    import traceback
    traceback.print_exc()
