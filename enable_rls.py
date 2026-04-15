import os
import psycopg2
from dotenv import load_dotenv

# Load connection string from .env if running locally
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ No DATABASE_URL found.")
    exit(1)

def enable_rls():
    try:
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL)
        c = conn.cursor()

        # List of tables to secure
        tables = ["users", "groups", "admins"]

        for table in tables:
            print(f"Enabling Row-Level Security on '{table}'...")
            try:
                c.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
            except Exception as e:
                print(f"Warning on table {table}: {e}")

        conn.commit()
        print("✅ Row-Level Security enabled on all tables.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    enable_rls()
