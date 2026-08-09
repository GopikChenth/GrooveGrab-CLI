"""
SQLite Database Storage for Download History & Queue State
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional
from platformdirs import user_data_dir

from groovegrab.core.models import DownloadTask, DownloadStatus


class TaskStorage:
    def __init__(self, db_path: Optional[Path] = None):
        if not db_path:
            try:
                data_dir = Path(user_data_dir("groovegrab"))
                data_dir.mkdir(parents=True, exist_ok=True)
                db_path = data_dir / "groovegrab.db"
            except Exception:
                data_dir = Path("./.groovegrab_config")
                data_dir.mkdir(parents=True, exist_ok=True)
                db_path = data_dir / "groovegrab.db"
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_tasks (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        status TEXT NOT NULL,
                        output_path TEXT,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        task_json TEXT NOT NULL
                    )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_download_tasks_created_at "
                "ON download_tasks(created_at DESC)"
            )
            conn.commit()

    def save_task(self, task: DownloadTask) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                    INSERT INTO download_tasks
                    (id, title, artist, provider, status, output_path, error_message, task_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        title = excluded.title,
                        artist = excluded.artist,
                        provider = excluded.provider,
                        status = excluded.status,
                        output_path = excluded.output_path,
                        error_message = excluded.error_message,
                        task_json = excluded.task_json
                """, (
                    task.id,
                    task.track.title,
                    task.track.artist,
                    task.track.provider_name,
                    task.status.value,
                    task.output_path,
                    task.error_message,
                    json.dumps(task.model_dump(mode="json"))
                ))
            conn.commit()

    def list_tasks(self, limit: int = 50) -> List[DownloadTask]:
        if limit < 1:
            return []
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT task_json FROM download_tasks ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        tasks = []
        for row in rows:
            try:
                tasks.append(DownloadTask.model_validate_json(row["task_json"]))
            except ValueError:
                # A corrupt historical row must not make the history command unusable.
                continue
        return tasks
