"""
Migration script to add user preference columns to the users table.
Run this once after deploying to add the new columns.

Usage: python migrate_add_user_preferences.py
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

engine = create_engine(DATABASE_URL)

# SQL to add the new columns (PostgreSQL)
migration_sql = """
-- Add gender_preference column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'gender_preference'
    ) THEN
        ALTER TABLE users ADD COLUMN gender_preference VARCHAR DEFAULT 'either';
    END IF;
END $$;

-- Add style_preferences column if it doesn't exist (JSON type)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'style_preferences'
    ) THEN
        ALTER TABLE users ADD COLUMN style_preferences JSON DEFAULT '[]';
    END IF;
END $$;
"""

if __name__ == "__main__":
    print("Running migration to add user preference columns...")

    with engine.connect() as conn:
        conn.execute(text(migration_sql))
        conn.commit()

    print("Migration completed successfully!")
    print("- Added gender_preference column (default: 'either')")
    print("- Added style_preferences column (default: [])")
