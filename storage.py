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
        c.execute("""
            CREATE TABLE IF NOT EXISTS snippets (
                user_id  TEXT NOT NULL,
                name     TEXT NOT NULL,
                code     TEXT NOT NULL,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, name)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS run_history (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                code    TEXT NOT NULL,
                output  TEXT NOT NULL DEFAULT '',
                ran_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


# ── Snippet storage ────────────────────────────────────────────────

def save_snippet(user_id: str, name: str, code: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO snippets (user_id, name, code) VALUES (?, ?, ?)",
            (user_id, name, code),
        )


def get_snippet(user_id: str, name: str) -> str | None:
    with _conn() as c:
        row = c.execute(
            "SELECT code FROM snippets WHERE user_id = ? AND name = ?",
            (user_id, name),
        ).fetchone()
    return row["code"] if row else None


def list_snippets(user_id: str) -> list[tuple[str, str]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT name, saved_at FROM snippets WHERE user_id = ? ORDER BY name",
            (user_id,),
        ).fetchall()
    return [(row["name"], row["saved_at"]) for row in rows]


def delete_snippet(user_id: str, name: str) -> bool:
    with _conn() as c:
        cur = c.execute(
            "DELETE FROM snippets WHERE user_id = ? AND name = ?",
            (user_id, name),
        )
    return cur.rowcount > 0


# ── Run history ────────────────────────────────────────────────────

def add_history(user_id: str, code: str, output: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO run_history (user_id, code, output) VALUES (?, ?, ?)",
            (user_id, code, output),
        )
        c.execute(
            """DELETE FROM run_history
               WHERE user_id = ? AND id NOT IN (
                   SELECT id FROM run_history WHERE user_id = ?
                   ORDER BY ran_at DESC LIMIT 10
               )""",
            (user_id, user_id),
        )


def get_history(user_id: str, limit: int = 5) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """SELECT code, output, ran_at FROM run_history
               WHERE user_id = ? ORDER BY ran_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]
