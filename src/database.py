"""Module for database management.

Database structure:
    - users: user information linking Discord and Last.fm accounts
    - user_preferences: user preferences for tracking, notifications, etc...
    - featured_albums: record of all featured albums
"""

import os
import random
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

# Get data directory from environment or use default
DATA_DIR = Path(os.environ.get("PVC_DATA_DIR", "./data"))
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "pvc.db"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Get a database connection. Creates a fresh connection per operation."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init():
    """Initialize database and create tables if they don't exist."""
    with get_connection() as conn:
        cursor = conn.cursor()

        sql_statements = [
            """CREATE TABLE IF NOT EXISTS users (
                discord_id INTEGER PRIMARY KEY UNIQUE NOT NULL,
                lastfm_username TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                is_special BOOLEAN DEFAULT 0
            )""",
            """CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                track BOOLEAN DEFAULT 1,
                notify BOOLEAN DEFAULT 0,
                double_track BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (discord_id) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS featured_albums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lastfm_username TEXT NOT NULL,
                artist_name TEXT NOT NULL,
                artist_url TEXT,
                album_name TEXT NOT NULL,
                album_url TEXT,
                cover_url TEXT,
                featured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_current BOOLEAN DEFAULT 0,
                FOREIGN KEY (lastfm_username) REFERENCES users (lastfm_username) ON DELETE CASCADE
            )""",
        ]

        # Create indexes for better performance
        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users (discord_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_lastfm ON users (lastfm_username)",
            "CREATE INDEX IF NOT EXISTS idx_featured_current ON featured_albums (is_current)",
            "CREATE INDEX IF NOT EXISTS idx_featured_user_time ON featured_albums (lastfm_username, featured_at DESC)",
        ]

        for statement in sql_statements + index_statements:
            cursor.execute(statement)

        conn.commit()
        cursor.close()


# user management


def create_user(discord_id: int, lastfm_username: str) -> bool:
    """Create a new user with Discord and Last.fm connection."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (discord_id, lastfm_username) VALUES (?, ?)",
                (discord_id, lastfm_username),
            )

            cursor.execute(
                "INSERT OR IGNORE INTO user_preferences (user_id) VALUES (?)", (discord_id,)
            )

            conn.commit()
            cursor.close()

            return True
    except sqlite3.IntegrityError:
        return False  # User already exists


def delete_user(discord_id: int) -> bool:
    """Delete a user."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE discord_id = ?", (discord_id,))
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False


def get_num_users() -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        result = cursor.fetchone()
        cursor.close()
        return result[0]


def get_num_special_users() -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_special = 1")
        result = cursor.fetchone()
        cursor.close()
        return result[0]


def get_random_user(double_special_chance: bool = False) -> Optional[str]:
    """Get a random user.

    Args:
        double_special_chance: If True, special users are picked twice as often.
                               Used on Sundays for dues payers.
    """
    num_users = get_num_users()
    num_special = get_num_special_users()

    if num_users == 0:
        return None

    # On Sundays (double_special_chance=True), special users get 2x odds
    if double_special_chance and num_special > 0:
        if random.random() < num_special / (num_users + num_special):
            return get_random_special_user()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT lastfm_username FROM users ORDER BY RANDOM() LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        return result["lastfm_username"] if result else None


def get_random_special_user() -> Optional[str]:
    """Get a random special user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT lastfm_username FROM users WHERE is_special = 1 ORDER BY RANDOM() LIMIT 1"
        )
        result = cursor.fetchone()
        cursor.close()
        return result["lastfm_username"] if result else None


def get_lastfm_user(discord_id: int) -> Optional[str]:
    """Get Last.fm username by Discord ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT lastfm_username FROM users WHERE discord_id = ?", (discord_id,))
        result = cursor.fetchone()
        cursor.close()
        return result["lastfm_username"] if result else None


def get_discord_id(lastfm_user: str) -> Optional[int]:
    """Get Discord ID by Last.fm username."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT discord_id FROM users WHERE lastfm_username = ?", (lastfm_user,))
        result = cursor.fetchone()
        cursor.close()
        return result["discord_id"] if result else None


def set_lfm_discord_connection(discord_id: int, lastfm_user: str) -> bool:
    """Create or update the connection between Discord and Last.fm accounts."""
    return create_user(discord_id, lastfm_user)


# featured album functions


def set_featured_album(
    lastfm_user: str,
    artist_name: str,
    artist_url: str,
    album_name: str,
    album_url: str,
    cover_url: str,
) -> bool:
    """Set a new featured album and mark it as current."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Mark all previous albums as not current
            cursor.execute("UPDATE featured_albums SET is_current = 0 WHERE is_current = 1")

            cursor.execute(
                """INSERT INTO featured_albums
                   (lastfm_username, artist_name, artist_url, album_name, album_url, cover_url, is_current)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (lastfm_user, artist_name, artist_url, album_name, album_url, cover_url),
            )

            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"Error setting featured album: {e}")
        return False


def get_featured_album() -> Optional[dict]:
    """Get the current featured album."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT fa.*
               FROM featured_albums fa
               WHERE fa.is_current = 1
               ORDER BY fa.featured_at DESC"""
        )
        result = cursor.fetchone()
        cursor.close()

        if not result:
            return None

        return {
            "member_l": result["lastfm_username"],
            "artist_name": result["artist_name"],
            "artist_url": result["artist_url"],
            "album": result["album_name"],
            "album_url": result["album_url"],
            "cover_url": result["cover_url"],
            "timestamp": result["featured_at"],
        }


def get_featured_log(lastfm_user: str) -> Optional[list[dict]]:
    """Get featured album history for a specific user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT fa.* FROM featured_albums fa
               WHERE fa.lastfm_username = ?
               ORDER BY fa.featured_at DESC""",
            (lastfm_user,),
        )
        results = cursor.fetchall()
        cursor.close()

        if not results:
            return None

        return [dict(row) for row in results]


# preferences functions


def get_preferences(discord_id: int) -> Optional[dict]:
    """Get user preferences by Discord ID."""
    if not discord_id:
        return None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (discord_id,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            return {
                "discord_id": discord_id,
                "track": result["track"],
                "notify": result["notify"],
                "double_track": result["double_track"],
            }
        return None


def set_preferences(discord_id: int, preferences: dict) -> bool:
    """Set user preferences."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE user_preferences
                   SET track = ?, notify = ?, double_track = ?
                   WHERE user_id = ?""",
                (
                    preferences.get("track"),
                    preferences.get("notify"),
                    preferences.get("double_track"),
                    discord_id,
                ),
            )
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"Error setting preferences: {e}")
        return False


def get_is_special(discord_id: int) -> bool:
    """Get whether a user is special."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_special FROM users WHERE discord_id = ?", (discord_id,))
        result = cursor.fetchone()
        cursor.close()
        return result["is_special"] if result else False
