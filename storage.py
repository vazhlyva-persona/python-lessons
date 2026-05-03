"""
SQLite-backed progress storage shared by the web app and Telegram bot.

User IDs are namespaced strings:
  web:  "web_<uuid>"   (cookie)
  bot:  "tg_<int>"     (Telegram user id)
"""

import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "progress.db")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                user_id   TEXT    NOT NULL,
                lesson_id INTEGER NOT NULL,
                done_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, lesson_id)
            )
        """)


def get_done(user_id: str) -> set[int]:
    with _conn() as c:
        rows = c.execute(
            "SELECT lesson_id FROM progress WHERE user_id = ?", (user_id,)
        ).fetchall()
    return {row["lesson_id"] for row in rows}


def mark_done(user_id: str, lesson_id: int) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO progress (user_id, lesson_id) VALUES (?, ?)",
            (user_id, lesson_id),
        )


def reset_progress(user_id: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM progress WHERE user_id = ?", (user_id,))
