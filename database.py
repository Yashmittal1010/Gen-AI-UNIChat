"""
UNIchat Database Layer
SQLite storage for chat sessions, messages, and analytics.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


DB_PATH = Path("data/unichat.db")


def get_connection() -> sqlite3.Connection:
    """Get a database connection, creating the DB if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_active TEXT NOT NULL DEFAULT (datetime('now')),
            message_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'bot')),
            content TEXT NOT NULL,
            backend TEXT DEFAULT 'rag-only',
            sources TEXT DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            matched_section TEXT,
            matched_category TEXT,
            match_score REAL,
            backend TEXT,
            response_time_ms INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_analytics_query ON analytics(created_at);
    """)
    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


def create_session() -> str:
    """Create a new chat session, return session ID."""
    sid = str(uuid.uuid4())[:8]
    conn = get_connection()
    conn.execute("INSERT INTO sessions (id) VALUES (?)", (sid,))
    conn.commit()
    conn.close()
    return sid


def save_message(session_id: str, role: str, content: str,
                 backend: str = "rag-only", sources: Optional[list] = None):
    """Save a chat message to the database."""
    conn = get_connection()

    # Ensure session exists
    row = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        conn.execute("INSERT INTO sessions (id) VALUES (?)", (session_id,))

    conn.execute(
        "INSERT INTO messages (session_id, role, content, backend, sources) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, backend, json.dumps(sources or [])),
    )
    conn.execute(
        "UPDATE sessions SET last_active = datetime('now'), message_count = message_count + 1 WHERE id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()


def log_analytics(query: str, section: str = "", category: str = "",
                  score: float = 0.0, backend: str = "", response_ms: int = 0):
    """Log query analytics."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO analytics (query, matched_section, matched_category, match_score, backend, response_time_ms) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (query, section, category, score, backend, response_ms),
    )
    conn.commit()
    conn.close()


def get_session_history(session_id: str, limit: int = 50) -> list[dict]:
    """Get chat history for a session."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT role, content, backend, created_at FROM messages "
        "WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_stats() -> dict:
    """Get overall chatbot statistics."""
    conn = get_connection()
    stats = {
        "total_sessions": conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
        "total_messages": conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
        "total_queries": conn.execute("SELECT COUNT(*) FROM analytics").fetchone()[0],
        "avg_match_score": conn.execute(
            "SELECT ROUND(AVG(match_score), 3) FROM analytics WHERE match_score > 0"
        ).fetchone()[0] or 0,
        "top_sections": [
            dict(r) for r in conn.execute(
                "SELECT matched_section as section, COUNT(*) as count "
                "FROM analytics WHERE matched_section != '' "
                "GROUP BY matched_section ORDER BY count DESC LIMIT 5"
            ).fetchall()
        ],
    }
    conn.close()
    return stats


# Initialize on import
init_db()


if __name__ == "__main__":
    print("Database initialized. Stats:")
    print(json.dumps(get_stats(), indent=2))
