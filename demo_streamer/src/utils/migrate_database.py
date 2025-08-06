#!/usr/bin/env python3
"""
Database migration script to add avatar_id column to stream_sessions table
"""

import sqlite3
import os
from pathlib import Path


def migrate_database():
    """Add avatar_id column to stream_sessions table"""

    # Database path
    db_path = Path("virtual_streamer.db")

    if not db_path.exists():
        print(f"Database file {db_path} not found!")
        return False

    print(f"Migrating database: {db_path}")

    try:
        # Connect to database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check if avatar_id column already exists
        cursor.execute("PRAGMA table_info(stream_sessions)")
        columns = [row[1] for row in cursor.fetchall()]

        if "avatar_id" in columns:
            print("✓ avatar_id column already exists in stream_sessions table")
            conn.close()
            return True

        print("Adding avatar_id column to stream_sessions table...")

        # Check if avatars table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='avatars'"
        )
        if not cursor.fetchone():
            print("Creating avatars table first...")
            create_avatars_table = """
            CREATE TABLE avatars (
                id INTEGER PRIMARY KEY,
                video_path VARCHAR(500) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                is_prepared BOOLEAN DEFAULT 0,
                bbox_shift INTEGER DEFAULT 0,
                preparation_status VARCHAR(50) DEFAULT 'pending',
                file_size INTEGER,
                duration FLOAT,
                resolution VARCHAR(20),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_avatars_table)
            print("✓ Created avatars table")

        # Add avatar_id column to stream_sessions
        cursor.execute("ALTER TABLE stream_sessions ADD COLUMN avatar_id INTEGER")
        print("✓ Added avatar_id column to stream_sessions")

        # Check if there are existing sessions
        cursor.execute("SELECT COUNT(*) FROM stream_sessions")
        session_count = cursor.fetchone()[0]

        if session_count > 0:
            print(f"Found {session_count} existing sessions")

            # Create a default avatar for existing sessions
            default_avatar_path = "../MuseTalk/data/video/yongen.mp4"
            cursor.execute(
                """
                INSERT OR IGNORE INTO avatars (video_path, name, is_prepared, bbox_shift, preparation_status)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    default_avatar_path,
                    "Default Avatar (Migration)",
                    False,
                    0,
                    "pending",
                ),
            )

            # Get the avatar ID
            cursor.execute(
                "SELECT id FROM avatars WHERE video_path = ?", (default_avatar_path,)
            )
            avatar_row = cursor.fetchone()

            if avatar_row:
                avatar_id = avatar_row[0]
                # Update existing sessions to use this avatar
                cursor.execute(
                    "UPDATE stream_sessions SET avatar_id = ? WHERE avatar_id IS NULL",
                    (avatar_id,),
                )
                updated_sessions = cursor.rowcount
                print(
                    f"✓ Updated {updated_sessions} existing sessions with default avatar (ID: {avatar_id})"
                )
            else:
                print("⚠ Warning: Could not create default avatar")

        # Commit changes
        conn.commit()
        conn.close()

        print("✅ Database migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        if "conn" in locals():
            conn.rollback()
            conn.close()
        return False


def verify_migration():
    """Verify that migration was successful"""
    db_path = Path("virtual_streamer.db")

    if not db_path.exists():
        print("Database file not found for verification")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check stream_sessions table structure
        cursor.execute("PRAGMA table_info(stream_sessions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        if "avatar_id" not in columns:
            print("❌ avatar_id column not found in stream_sessions")
            return False

        print("✓ avatar_id column exists in stream_sessions")

        # Check avatars table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='avatars'"
        )
        if not cursor.fetchone():
            print("❌ avatars table not found")
            return False

        print("✓ avatars table exists")

        # Check avatar count
        cursor.execute("SELECT COUNT(*) FROM avatars")
        avatar_count = cursor.fetchone()[0]
        print(f"✓ Found {avatar_count} avatars in database")

        # Check sessions with avatar_id
        cursor.execute(
            "SELECT COUNT(*) FROM stream_sessions WHERE avatar_id IS NOT NULL"
        )
        sessions_with_avatar = cursor.fetchone()[0]
        print(f"✓ Found {sessions_with_avatar} sessions with avatar_id")

        conn.close()
        print("✅ Migration verification passed!")
        return True

    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False


if __name__ == "__main__":
    print("=== Database Migration Script ===")
    print("Adding avatar_id column to stream_sessions table")
    print()

    success = migrate_database()

    if success:
        print("\n=== Verifying Migration ===")
        verify_migration()
    else:
        print("\n❌ Migration failed!")

    print("\nDone!")
