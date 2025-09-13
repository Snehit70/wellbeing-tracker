"""
Database Migration Script for Digital Wellbeing Tracker

This script inspects the SQLite database and applies necessary schema changes
to bring it up to date with the latest version of the application.

It is designed to be idempotent, meaning it can be run multiple times without
causing errors or corrupting data.
"""

import sqlite3
from pathlib import Path
import sys

# Ensure the script can find project modules if run from root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data/wellbeing.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    if not DB_PATH.exists():
        print(f"❌ Error: Database file not found at {DB_PATH}")
        print("Please run the collector at least once to create the database.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def get_table_columns(cursor, table_name):
    """Returns a list of column names for a given table."""
    cursor.execute(f"PRAGMA table_info({table_name});")
    return [row[1] for row in cursor.fetchall()]

def add_column_if_not_exists(cursor, table_name, column_name, column_type):
    """Adds a column to a table if it doesn't already exist."""
    columns = get_table_columns(cursor, table_name)
    if column_name not in columns:
        print(f"  -> Adding column '{column_name}' to table '{table_name}'...")
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};")
            print(f"     ✅ Done.")
            return True
        except sqlite3.OperationalError as e:
            print(f"     ❌ Error adding column: {e}")
            return False
    else:
        print(f"  -> Column '{column_name}' already exists in '{table_name}'. Skipping.")
        return False

def main():
    """Main function to run the database migrations."""
    print("🚀 Starting database migration check...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    migrations_applied = 0
    
    print("\n🔍 Checking 'events' table...")
    if add_column_if_not_exists(cursor, "events", "website_url", "TEXT"):
        migrations_applied += 1
    if add_column_if_not_exists(cursor, "events", "website_title", "TEXT"):
        migrations_applied += 1
        
    print("\n🔍 Checking 'hourly_usage' table...")
    if add_column_if_not_exists(cursor, "hourly_usage", "website_url", "TEXT"):
        migrations_applied += 1

    print("\n🔍 Checking 'daily_usage' table...")
    if add_column_if_not_exists(cursor, "daily_usage", "website_url", "TEXT"):
        migrations_applied += 1

    # The schema also updated uniqueness constraints, which are hard to migrate
    # in SQLite. We will note this but not attempt to automate it.
    print("\n📝 Note: This script adds columns but does not modify UNIQUE constraints.")
    print("   For full schema alignment, a new database may be required if starting from a very old version.")

    conn.commit()
    conn.close()
    
    print("\n" + "="*30)
    if migrations_applied > 0:
        print(f"🎉 Migration complete. {migrations_applied} change(s) applied.")
    else:
        print("✅ Your database schema is already up to date.")
    print("="*30)

if __name__ == "__main__":
    main()
