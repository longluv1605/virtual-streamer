#!/usr/bin/env python3
"""
Clear and recreate database with proper schema
"""

import os
import sqlite3
from pathlib import Path


def clear_and_recreate_database():
    """Delete existing database and recreate with proper schema"""

    # Database path
    db_path = Path("virtual_streamer.db")

    if db_path.exists():
        print(f"Deleting existing database: {db_path}")
        os.remove(db_path)
        print("✓ Database deleted")
    else:
        print("No existing database found")

    print("✓ Database will be recreated automatically when the app starts")
    print("✓ Sample data will be initialized")

    return True


if __name__ == "__main__":
    print("=== Database Reset Script ===")
    print("This will delete the existing database and recreate it with proper schema")
    print()

    # Confirm action
    response = input("Are you sure you want to delete the database? (y/N): ")
    if response.lower() in ["y", "yes"]:
        success = clear_and_recreate_database()

        if success:
            print("\n✅ Database reset completed!")
            print(
                "Please restart the application to recreate the database with proper schema."
            )
        else:
            print("\n❌ Database reset failed!")
    else:
        print("Operation cancelled.")

    print("\nDone!")
