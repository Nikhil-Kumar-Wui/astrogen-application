import os
import psycopg2
from urllib.parse import quote_plus

host = "db.vudjkrauybcsaxetmtgn.supabase.co"
user = "postgres"
password_raw = "Sr%53rj2#DQvcfg"

passwords_to_try = [
    password_raw,
    password_raw.replace("#", "%23"),
    "Sr%2553rj2%23DQvcfg",
    "Sr%2553rj2#DQvcfg",
]

# Let's also try constructing it using quote_plus
try:
    passwords_to_try.append(quote_plus(password_raw))
except:
    pass

print("Starting Supabase connection tests...")

for idx, pwd in enumerate(passwords_to_try):
    # Try port 5432 (direct)
    print(f"\nTest {idx+1}a (Port 5432): Trying password: {pwd}")
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=user,
            password=pwd,
            host=host,
            port=5432,
            connect_timeout=5
        )
        print("--> SUCCESS on Port 5432!")
        conn.close()
        break
    except Exception as e:
        print(f"--> Failed: {e}")

    # Try port 6543 (pooler)
    pooler_host = "aws-0-us-east-1.pooler.supabase.com" # standard Supabase pooler host
    print(f"Test {idx+1}b (Port 6543): Trying password: {pwd}")
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=user,
            password=pwd,
            host=pooler_host,
            port=6543,
            connect_timeout=5
        )
        print("--> SUCCESS on Port 6543!")
        conn.close()
        break
    except Exception as e:
        print(f"--> Failed: {e}")
