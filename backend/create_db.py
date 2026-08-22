import sys
import os
import io

# Prevent Windows CP1252 stdout encoding crashes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings

def create_database_if_not_exists():
    user = settings.POSTGRES_USER
    password = settings.POSTGRES_PASSWORD
    host = settings.POSTGRES_HOST
    port = settings.POSTGRES_PORT
    target_db = settings.POSTGRES_DB

    print(f"Connecting to PostgreSQL as user '{user}' on {host}:{port}...")

    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s;", (target_db,))
        exists = cursor.fetchone()

        if not exists:
            print(f"Database '{target_db}' does not exist. Creating it now...")
            cursor.execute(f'CREATE DATABASE "{target_db}";')
            print(f"Database '{target_db}' created successfully!")
        else:
            print(f"Database '{target_db}' already exists.")

        cursor.close()
        conn.close()

        print("Initializing tables and extensions...")
        from app.database import init_db
        if init_db():
            print("All tables & vector extensions initialized successfully!")
        else:
            print("Table initialization finished with warnings.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_database_if_not_exists()
