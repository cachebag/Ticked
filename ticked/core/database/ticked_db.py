from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_data_home() -> Path:
    # Check for the XDG_DATA_HOME environment variable
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home)
    # Fallback to the default
    return Path.home() / ".local" / "share"


class CalendarDB:
    def __init__(self, db_path: str = None):
        if db_path is None:
            data_dir = get_data_home() / "ticked"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "tick.db")
        else:
            self.db_path = db_path

        self._create_tables()
        self._migrate_database()

    def _migrate_database(self) -> None:
        """Migrate database to new schema while preserving user data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Migration check
            cursor.execute("PRAGMA table_info(tasks)")
            columns = {col[1]: col[2] for col in cursor.fetchall()}

            if "start_time" in columns and columns["start_time"] == "TIME":
                cursor.execute(
                    """
                    CREATE TABLE tasks_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        due_date TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed BOOLEAN DEFAULT 0,
                        in_progress BOOLEAN DEFAULT 0,
                        caldav_uid TEXT
                    )
                """
                )

                cursor.execute(
                    """
                    INSERT INTO tasks_new 
                    SELECT id, title, description, 
                           date(due_date) as due_date,
                           time(start_time) as start_time,
                           time(end_time) as end_time,
                           created_at, completed, in_progress, caldav_uid
                    FROM tasks
                """
                )

                cursor.execute("DROP TABLE tasks")
                cursor.execute("ALTER TABLE tasks_new RENAME TO tasks")

                conn.commit()

    def _create_tables(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed BOOLEAN DEFAULT 0,
                    in_progress BOOLEAN DEFAULT 0,
                    caldav_uid TEXT
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    date TEXT PRIMARY KEY,
                    content TEXT,
                    updated_at TIMESTAMP
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS spotify_auth (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    access_token TEXT,
                    refresh_token TEXT,
                    token_expiry TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS caldav_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    url TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    last_sync TIMESTAMP,
                    selected_calendar TEXT
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notes_preferences (
                    date TEXT PRIMARY KEY,
                    view_mode TEXT DEFAULT 'edit',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.commit()

    def add_task(
        self,
        title: str,
        due_date: str,
        start_time: str,
        end_time: str,
        description: str = "",
        caldav_uid: str = None,
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tasks (title, description, due_date, start_time, end_time, caldav_uid)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (title, description, due_date, start_time, end_time, caldav_uid),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def is_first_launch(self) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'first_launch'")
            result = cursor.fetchone()
            return result is None

    def save_caldav_config(
        self, url: str, username: str, password: str, calendar: str
    ) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO caldav_config 
                (id, url, username, password, selected_calendar, last_sync)
                VALUES (1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (url, username, password, calendar),
            )
            conn.commit()
            return True

    def get_caldav_config(self) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM caldav_config WHERE id = 1")
            result = cursor.fetchone()
            return dict(result) if result else None

    def mark_first_launch_complete(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('first_launch', 'completed')
            """
            )
            conn.commit()

    def get_tasks_for_date(self, date: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM tasks 
                WHERE due_date = ?
                ORDER BY start_time
            """,
                (date,),
            )

            return [dict(row) for row in cursor.fetchall()]

    def update_task(self, task_id: int, **kwargs) -> bool:
        valid_fields = {
            "title",
            "description",
            "due_date",
            "start_time",
            "end_time",
            "completed",
            "in_progress",
        }
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}

        if not update_fields:
            return False

        query_parts = []
        values = []
        for field in update_fields:
            query_parts.append(f"{field} = ?")
            values.append(update_fields[field])

        values.append(task_id)

        query = "UPDATE tasks SET " + ", ".join(query_parts) + " WHERE id = ?"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
        return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_tasks_not_in_uids(self, uids: set[str]) -> None:
        if not uids:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(uids))
            query = """
                DELETE FROM tasks 
                WHERE caldav_uid IS NOT NULL 
                AND caldav_uid NOT IN ({})
            """.format(
                placeholders
            )

            cursor.execute(query, tuple(uids))
            conn.commit()

    def save_notes(self, date: str, content: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO notes (date, content, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(date) DO UPDATE SET
                    content = excluded.content,
                    updated_at = CURRENT_TIMESTAMP
            """,
                (date, content),
            )
            conn.commit()
            return True

    def get_notes(self, date: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM notes WHERE date = ?", (date,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_tasks_between_dates(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM tasks 
                WHERE due_date BETWEEN ? AND ?
                ORDER BY due_date, start_time
            """,
                (start_date, end_date),
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_upcoming_tasks(
        self, start_date: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM tasks 
                WHERE due_date > ? AND due_date <= date(?, '+' || ? || ' days')
                ORDER BY due_date, start_time
            """,
                (start_date, start_date, days),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_month_stats(self, year: int, month: int) -> dict:
        try:
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                next_year = year + 1
                next_month = 1
            else:
                next_year = year
                next_month = month + 1
            end_date = f"{next_year}-{next_month:02d}-01"

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = """
                    SELECT 
                        COUNT(*) AS total,
                        SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) AS completed,
                        SUM(CASE WHEN in_progress = 1 THEN 1 ELSE 0 END) AS in_progress
                    FROM tasks 
                    WHERE due_date >= ? AND due_date < ?
                """

                cursor.execute(query, (start_date, end_date))
                result = cursor.fetchone()

                total = result["total"] or 0
                completed = result["completed"] or 0
                in_progress = result["in_progress"] or 0

                completion_pct = round((completed / total * 100) if total > 0 else 0, 1)
                grade = (
                    "A"
                    if completion_pct >= 90
                    else (
                        "B"
                        if completion_pct >= 80
                        else (
                            "C"
                            if completion_pct >= 70
                            else "D" if completion_pct >= 60 else "F"
                        )
                    )
                )

                return {
                    "total": total,
                    "completed": completed,
                    "in_progress": in_progress,
                    "completion_pct": completion_pct,
                    "grade": grade,
                }
        except Exception as e:
            print(f"Error getting month stats: {e}")
            return {
                "total": 0,
                "completed": 0,
                "in_progress": 0,
                "completion_pct": 0,
                "grade": "N/A",
            }

    def save_spotify_tokens(
        self, access_token: str, refresh_token: str, expires_at: datetime
    ) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO spotify_auth 
                (id, access_token, refresh_token, token_expiry)
                VALUES (1, ?, ?, ?)
            """,
                (access_token, refresh_token, expires_at),
            )
            conn.commit()
            return True

    def get_spotify_tokens(self) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM spotify_auth WHERE id = 1")
            result = cursor.fetchone()
            return dict(result) if result else None

    def get_task_by_uid(self, caldav_uid: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM tasks WHERE caldav_uid = ?
            """,
                (caldav_uid,),
            )
            result = cursor.fetchone()
            return dict(result) if result else None

    def save_calendar_view_preference(self, is_month_view: bool) -> None:
        """Save the user's preferred calendar view."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('calendar_view', ?)
            """,
                (str(int(is_month_view)),),
            )
            conn.commit()

    def get_calendar_view_preference(self) -> bool:
        """Get the user's preferred calendar view. Returns False for week view by default."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'calendar_view'")
            result = cursor.fetchone()
            return bool(int(result[0])) if result else False

    def save_last_update_check(self) -> None:
        """Save the timestamp of the last update check."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('last_update_check', CURRENT_TIMESTAMP)
            """
            )
            conn.commit()

    def should_check_for_updates(self) -> bool:
        """Check if we should look for updates (once per day)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'last_update_check'")
            result = cursor.fetchone()
            if not result:
                return True
            last_check = datetime.fromisoformat(result[0])
            return (datetime.now() - last_check).days >= 1

    def save_theme_preference(self, theme: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('theme', ?)",
                (theme,),
            )
            conn.commit()

    def get_theme_preference(self) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'theme'")
            result = cursor.fetchone()
            return result[0] if result else None

    def save_notes_view_mode(self, date: str, view_mode: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO notes_preferences (date, view_mode, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(date) DO UPDATE SET
                    view_mode = excluded.view_mode,
                    updated_at = CURRENT_TIMESTAMP
            """,
                (date, view_mode),
            )
            conn.commit()
            return True

    def get_notes_view_mode(self, date: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT view_mode FROM notes_preferences WHERE date = ?", (date,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
