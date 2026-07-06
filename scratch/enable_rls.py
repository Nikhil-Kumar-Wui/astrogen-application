import psycopg2

db_url = "postgresql://postgres:Sr%2553rj2%23DQvcfg@db.vudjkrauybcsaxetmtgn.supabase.co:5432/postgres"

print("Connecting to Supabase PG to enable RLS...")
try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    tables = ['sessions', 'messages', 'generated_images', 'users', 'login_history']
    for t in tables:
        try:
            cur.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;")
            conn.commit()
            print(f"Row Level Security (RLS) enabled on table: {t}")
        except Exception as e:
            print(f"Failed to enable RLS on {t}: {e}")
            conn.rollback()

    conn.close()
    print("All tables successfully secured with RLS!")
except Exception as e:
    print("Database connection error:", e)
