import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

class CalendarDB:
    def __init__(self, db_path: str = "calendar.db"):
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date DATE NOT NULL,
                    due_time TIME NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed BOOLEAN DEFAULT 0,
                    in_progress BOOLEAN DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    date TEXT PRIMARY KEY,
                    content TEXT,
                    updated_at TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS spotify_auth (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    access_token TEXT,
                    refresh_token TEXT,
                    token_expiry TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
                           
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
                )
            """)

            cursor.execute("SELECT id, due_time FROM tasks")
            tasks = cursor.fetchall()
            for task_id, due_time in tasks:
                try:
                    time_obj = datetime.strptime(due_time, "%H:%M")
                    formatted_time = time_obj.strftime("%I:%M %p")
                    cursor.execute("UPDATE tasks SET due_time = ? WHERE id = ?", (formatted_time, task_id))
                except:
                    pass

            conn.commit()
    
    def add_task(self, title: str, due_date: str, due_time: str, description: str = "") -> int:
        time_obj = datetime.strptime(due_time, "%H:%M")
        formatted_time = time_obj.strftime("%I:%M %p")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (title, description, due_date, due_time)
                VALUES (?, ?, ?, ?)
            """, (title, description, due_date, formatted_time))
            conn.commit()
            return cursor.lastrowid or 0
        
    def is_first_launch(self) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'first_launch'")
            result = cursor.fetchone()
            return result is None

    def mark_first_launch_complete(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('first_launch', 'completed')
            """)
            conn.commit()
        
    def get_tasks_for_date(self, date: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE due_date = ?
                ORDER BY due_time
            """, (date,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_task(self, task_id: int, **kwargs) -> bool:
        valid_fields = {'title', 'description', 'due_date', 'due_time', 'completed', 'in_progress'}
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if 'due_time' in update_fields:
            time_obj = datetime.strptime(update_fields['due_time'], "%H:%M")
            update_fields['due_time'] = time_obj.strftime("%I:%M %p")
        
        if not update_fields:
            return False
        
        set_clause = ", ".join(f"{k} = ?" for k in update_fields)
        values = list(update_fields.values())
        values.append(task_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE tasks 
                SET {set_clause}
                WHERE id = ?
            """, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_task(self, task_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def save_notes(self, date: str, content: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notes (date, content, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(date) DO UPDATE SET
                    content = excluded.content,
                    updated_at = CURRENT_TIMESTAMP
            """, (date, content))
            conn.commit()
            return True
    
    def get_notes(self, date: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM notes WHERE date = ?", (date,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_tasks_between_dates(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE due_date BETWEEN ? AND ?
                ORDER BY due_date, due_time
            """, (start_date, end_date))
            
            return [dict(row) for row in cursor.fetchall()]

    def get_upcoming_tasks(self, start_date: str, days: int = 7) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE due_date > ? AND due_date <= date(?, '+' || ? || ' days')
                ORDER BY due_date, due_time
            """, (start_date, start_date, days))
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
                    "A" if completion_pct >= 90 else
                    "B" if completion_pct >= 80 else
                    "C" if completion_pct >= 70 else
                    "D" if completion_pct >= 60 else
                    "F"
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
    
    def save_spotify_tokens(self, access_token: str, refresh_token: str, expires_at: datetime) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO spotify_auth 
                (id, access_token, refresh_token, token_expiry)
                VALUES (1, ?, ?, ?)
            """, (access_token, refresh_token, expires_at))
            conn.commit()
            return True
    
    def get_spotify_tokens(self) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM spotify_auth WHERE id = 1")
            result = cursor.fetchone()
            return dict(result) if result else None