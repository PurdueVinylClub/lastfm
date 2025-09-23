"""Module for database management.

Database structure:
    - users: user information linking Discord and Last.fm accounts
    - user_preferences
    - featured_albums: record of all featured albums

Include list of special roles?
"""

import sqlite3
import csv
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import os

db: sqlite3.Connection = None

def init():
    """Initialize database connection and create tables if they don't exist."""
    global db
    db = sqlite3.connect('pvc.db')
    db.row_factory = sqlite3.Row  # Enable dict-like access to rows

    cursor = db.cursor()

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
            FOREIGN KEY (user_id) REFERENCES users (lastfm_username) ON DELETE CASCADE
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

    db.commit()
    cursor.close()

# user management

def create_user(discord_id: int, lastfm_username: str) -> bool:
    """Create a new user with Discord and Last.fm connection."""
    try:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO users (discord_id, lastfm_username) VALUES (?, ?)",
            (discord_id, lastfm_username)
        )

        # Create default preferences entry using discord_id as foreign key
        cursor.execute(
            "INSERT INTO user_preferences (user_id) VALUES (?)",
            (discord_id,)
        )

        db.commit()
        cursor.close()
        return True
    except sqlite3.IntegrityError:
        return False  # User already exists

def get_lastfm_user(discord_id: int) -> Optional[str]:
    """Get Last.fm username by Discord ID."""
    cursor = db.cursor()
    cursor.execute(
        "SELECT lastfm_username FROM users WHERE discord_id = ?",
        (discord_id,)
    )
    result = cursor.fetchone()
    cursor.close()
    return result['lastfm_username'] if result else None

def get_discord_id(lastfm_user: str) -> Optional[int]:
    """Get Discord ID by Last.fm username."""
    cursor = db.cursor()
    cursor.execute(
        "SELECT discord_id FROM users WHERE lastfm_username = ?",
        (lastfm_user,)
    )
    result = cursor.fetchone()
    cursor.close()
    return result['discord_id'] if result else None

def set_lfm_discord_connection(discord_id: int, lastfm_user: str) -> bool:
    """Create or update the connection between Discord and Last.fm accounts."""
    return create_user(discord_id, lastfm_user)

# featured album functions

def set_featured_album(lastfm_user: str, artist_name: str, artist_url: str,
                       album_name: str, album_url: str, cover_url: str) -> bool:
    """Set a new featured album and mark it as current."""
    try:
        cursor = db.cursor()

        # Mark all previous albums as not current
        cursor.execute(
            "UPDATE featured_albums SET is_current = 0 WHERE is_current = 1"
        )

        cursor.execute(
            """INSERT INTO featured_albums
               (lastfm_username, artist_name, artist_url, album_name, album_url, cover_url, is_current)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (lastfm_user, artist_name, artist_url, album_name, album_url, cover_url)
        )

        db.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error setting featured album: {e}")
        return False

def get_featured_album() -> Optional[Dict]:
    """Get the current featured album."""
    cursor = db.cursor()
    cursor.execute(
        """SELECT fa.*, u.discord_id, u.lastfm_username
           FROM featured_albums fa
           JOIN users u ON fa.lastfm_username = u.lastfm_username
           WHERE fa.is_current = 1
           LIMIT 1"""
    )
    result = cursor.fetchone()
    cursor.close()

    if result:
        return {
            'member_d': result['discord_id'],
            'member_l': result['lastfm_username'],
            'artist_name': result['artist_name'],
            'artist_url': result['artist_url'],
            'album': result['album_name'],
            'album_url': result['album_url'],
            'cover_url': result['cover_url'],
            'timestamp': result['featured_at']
        }
    return None

def get_featured_log(lastfm_user: str) -> List[Dict]:
    """Get featured album history for a specific user."""
    cursor = db.cursor()
    cursor.execute(
        """SELECT fa.* FROM featured_albums fa
           JOIN users u ON fa.lastfm_username = u.lastfm_username
           WHERE u.lastfm_username = ?
           ORDER BY fa.featured_at DESC""",
        (lastfm_user,)
    )
    results = cursor.fetchall()
    cursor.close()

    return [dict(row) for row in results]

# preferences functions

def get_preferences(discord_id: int) -> Optional[Dict]:
    """Get user preferences by Discord ID."""
    if not discord_id:
        return None

    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM user_preferences WHERE user_id = ?",
        (discord_id,)
    )
    result = cursor.fetchone()
    cursor.close()

    if result:
        return {
            'discord_id': discord_id,
            'track': result['track'],
            'notify': result['notify']
        }
    return None

def set_preferences(discord_id: int, preferences: Dict) -> bool:
    """Set user preferences."""
    try:
        cursor = db.cursor()
        cursor.execute(
            """UPDATE user_preferences
               SET track = ?, notify = ?
               WHERE user_id = ?""",
            (
                preferences.get('track'),
                preferences.get('notify'),
                discord_id
            )
        )
        db.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error setting preferences: {e}")
        return False