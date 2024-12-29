import sqlite3
from typing import Optional, List, Dict, Any

class CalendarDB:
    def __init__(self, db_path: str = "calendar.db"):
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
        
        # Create tasks table
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
        
        # Add in_progress column if it doesn't exist
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'in_progress' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN in_progress BOOLEAN DEFAULT 0")
        
        # Create notes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                content TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date)
            )
        """)
        
        conn.commit() 
    
    def add_task(self, title: str, due_date: str, due_time: str, description: str = "") -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (title, description, due_date, due_time)
                VALUES (?, ?, ?, ?)
            """, (title, description, due_date, due_time))
            conn.commit()
            return cursor.lastrowid or 0
    
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
        valid_fields = {'title', 'description', 'due_date', 'due_time', 'completed','in_progress'}
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
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
