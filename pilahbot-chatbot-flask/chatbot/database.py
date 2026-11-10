from contextlib import contextmanager
import sqlite3
from pathlib import Path


@contextmanager
def _connect(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(database_path):
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    with _connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                question TEXT NOT NULL,
                intent_id TEXT,
                intent_name TEXT,
                score REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_questions_created_at ON questions(created_at DESC)"
        )


def record_question(database_path, session_id, question, result, created_at):
    recognized = result["intent"] != "FB01"
    with _connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO questions
                (session_id, question, intent_id, intent_name, score, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                question,
                result["intent"] if recognized else None,
                result["intent_name"] if recognized else None,
                result["score"],
                created_at,
            ),
        )


def refresh_scores(database_path, score_message):
    with _connect(database_path) as connection:
        rows = connection.execute("SELECT id, question FROM questions").fetchall()
        connection.executemany(
            "UPDATE questions SET score = ? WHERE id = ?",
            [(score_message(row["question"]), row["id"]) for row in rows],
        )


def get_statistics(database_path):
    with _connect(database_path) as connection:
        summary = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN intent_id IS NOT NULL THEN 1 ELSE 0 END) AS recognized,
                COUNT(DISTINCT session_id) AS visitors
            FROM questions
            """
        ).fetchone()
        intent_rows = connection.execute(
            """
            SELECT COALESCE(intent_name, '(tidak dikenali)') AS intent, COUNT(*) AS count
            FROM questions
            GROUP BY intent_id, intent_name
            ORDER BY count DESC, intent COLLATE NOCASE
            """
        ).fetchall()
        unknown_rows = connection.execute(
            """
            SELECT question, score, created_at
            FROM questions
            WHERE intent_id IS NULL
            ORDER BY id DESC
            """
        ).fetchall()

    total = summary["total"] or 0
    recognized = summary["recognized"] or 0
    intents = [
        {
            "intent": row["intent"],
            "count": row["count"],
            "proportion": round(row["count"] * 100 / total, 1) if total else 0,
        }
        for row in intent_rows
    ]
    return {
        "total": total,
        "recognized": recognized,
        "unrecognized": total - recognized,
        "recognition_rate": round(recognized * 100 / total, 1) if total else 0,
        "visitors": summary["visitors"] or 0,
        "intents": intents,
        "unknown_questions": [dict(row) for row in unknown_rows],
    }
