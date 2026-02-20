"""
Migration script to add subscription tier columns to the users table.
Run this once to update your database schema.

Usage: python migrate_add_tiers.py
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.config import settings

def run_migration():
    """Add new subscription tier columns to users table."""

    print("Connecting to database...")
    engine = create_engine(settings.DATABASE_URL)

    # SQL commands to add the new columns
    migrations = [
        # Add subscription_tier column
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR DEFAULT 'free';
        """,

        # Add monthly_scans_used column
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS monthly_scans_used INTEGER DEFAULT 0;
        """,

        # Add monthly_scans_reset_at column
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS monthly_scans_reset_at TIMESTAMP WITH TIME ZONE;
        """,

        # Update existing users: set subscription_tier based on subscription_status
        """
        UPDATE users
        SET subscription_tier = CASE
            WHEN subscription_status = 'active' THEN 'unlimited'
            ELSE 'free'
        END
        WHERE subscription_tier IS NULL OR subscription_tier = '';
        """,
    ]

    with engine.connect() as conn:
        for i, sql in enumerate(migrations, 1):
            try:
                print(f"Running migration {i}...")
                conn.execute(text(sql))
                conn.commit()
                print(f"Migration {i} completed successfully.")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print(f"Migration {i} skipped (column already exists).")
                else:
                    print(f"Error in migration {i}: {e}")
                    # Continue with other migrations
                    conn.rollback()

    print("\nMigration completed!")
    print("You can now restart your server.")

if __name__ == "__main__":
    run_migration()
