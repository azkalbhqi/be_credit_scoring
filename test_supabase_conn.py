import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from core.config import settings

def test_connection():
    print(f"DATABASE_URL configured: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    try:
        engine = create_engine(settings.DATABASE_URL)
        print("Attempting to connect to Supabase PostgreSQL...")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        print("\nSUCCESS: Connected to Supabase PostgreSQL successfully!")
        print("Your backend is writing to Supabase, NOT local SQLite.")
    except Exception as e:
        print("\nFAILURE: Could not connect to Supabase PostgreSQL.")
        print(f"Error details: {e}")
        print("\nPlease check your credentials and make sure port 6543 is open.")

if __name__ == "__main__":
    test_connection()
