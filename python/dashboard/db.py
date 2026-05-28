"""SQLite connection manager for dashboard.db."""
import sqlite3
import secrets
import logging
from pathlib import Path
from .. import config

logger = logging.getLogger(__name__)


def get_db():
    """Get a new SQLite connection (WAL mode). Caller must close."""
    conn = sqlite3.connect(str(config.DASHBOARD_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist. Create default admin if no users."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL,
            acknowledged INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()

    # Create default admin user if no users exist
    try:
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        if row[0] == 0:
            import bcrypt
            password = secrets.token_hex(8)
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("admin", password_hash),
            )
            conn.commit()
            logger.warning(
                "Default admin user created: username=admin, password=%s",
                password,
            )
    except Exception as e:
        logger.error("Failed to create default admin user: %s", e)

    conn.close()
