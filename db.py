import sqlite3
import json
from datetime import datetime

DB_PATH = "./results.db"

class ResultsDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT    NOT NULL,
                    enabled_tools   TEXT,               -- JSON list of tool names
                    preloaded_info  TEXT,               -- JSON list of keys
                    system_prompt   TEXT,
                    reasoning       INTEGER NOT NULL,   -- 0 / 1
                    model           TEXT    NOT NULL,
                    query    TEXT    NOT NULL,
                    response        TEXT,
                    tool_call_count INTEGER DEFAULT 0,
                    duration_ms     INTEGER
                );

                CREATE TABLE IF NOT EXISTS tool_calls (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id      INTEGER NOT NULL REFERENCES calls(id),
                    tool_name   TEXT    NOT NULL,
                    arguments   TEXT,                   -- JSON
                    result      TEXT                    -- JSON
                );
            """)

    ##########
    # Write
    ##########
    def start_run(self, enabled_tools, preloaded_info, system_prompt, reasoning, model, query):
        with self._connect() as conn:
            calls = conn.execute(
                """INSERT INTO runs (timestamp, enabled_tools, preloaded_info, system_prompt, reasoning, model, query)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now().isoformat(),
                    json.dumps(enabled_tools),
                    json.dumps(preloaded_info),
                    system_prompt,
                    int(reasoning),
                    model,
                    query
                )
            )
            return calls.lastrowid

    def finish_run(self, run_id: int, response: str, tool_call_count: int, duration_ms: int):
        with self._connect() as conn:
            conn.execute(
                """UPDATE runs
                   SET response = ?, tool_call_count = ?, duration_ms = ?
                   WHERE id = ?""",
                (response, tool_call_count, duration_ms, run_id)
            )

    def log_tool_call(self, run_id: int, tool_name: str, arguments: dict, result):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO tool_calls (run_id, tool_name, arguments, result) VALUES (?, ?, ?, ?)",
                (run_id, tool_name, json.dumps(arguments), json.dumps(result))
            )

    ##########
    # Read
    ##########
    def get_run(self, run_id: int):
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            return dict(row) if row else None

    def get_tool_calls(self, run_id: int):
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tool_calls WHERE run_id = ?", (run_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def summary(self):
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, timestamp, model, reasoning, query,
                          tool_call_count, duration_ms,
                          CASE WHEN response IS NOT NULL THEN 1 ELSE 0 END AS completed
                   FROM runs ORDER BY id DESC"""
            ).fetchall()
            return [dict(r) for r in rows]