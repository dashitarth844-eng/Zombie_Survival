
import sqlite3
import os
from datetime import datetime

# Store the database inside the project folder.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "game_stats.db")


def get_connection():
    """Open a connection to the SQLite database."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    return sqlite3.connect(DATABASE_PATH)


def initialize_database():
    """Create the game history table if it doesn't exist."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                wave_reached INTEGER NOT NULL,
                score INTEGER NOT NULL,
                zombies_killed INTEGER NOT NULL,
                survival_seconds INTEGER NOT NULL,
                played_at TEXT NOT NULL
            )
        """)


def save_game(
    player_name,
    difficulty,
    wave_reached,
    score,
    zombies_killed,
    survival_seconds,
):
    """Save one completed game."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO game_history (
                player_name,
                difficulty,
                wave_reached,
                score,
                zombies_killed,
                survival_seconds,
                played_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            player_name,
            difficulty,
            wave_reached,
            score,
            zombies_killed,
            survival_seconds,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))


def get_top_scores(limit=10):
    """Return the highest-scoring games."""
    with get_connection() as connection:
        cursor = connection.execute("""
            SELECT player_name, difficulty, wave_reached,
                   score, zombies_killed, survival_seconds,
                   played_at
            FROM game_history
            ORDER BY score DESC, wave_reached DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()


def get_game_history(limit=20):
    """Return the most recently played games."""
    with get_connection() as connection:
        cursor = connection.execute("""
            SELECT player_name, difficulty, wave_reached,
                   score, zombies_killed, survival_seconds,
                   played_at
            FROM game_history
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()


# Create the table when this module is imported.
initialize_database()