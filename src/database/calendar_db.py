import sqlite3
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional, List, Dict, Any

class CalendarDB:
    def __init__(self, db_path: str = "calendar.db"):
        self.db_path = db_path
        self._connection = None
        self._transaction_count = 0
        self._cache = {}
        self._create_tables()
    
    @property
    def connection(self):
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def begin_transaction(self):
        self._transaction_count += 1
        if self._transaction_count == 1:
            self.connection.execute("BEGIN")

    def commit_transaction(self):
        self._transaction_count -= 1
        if self._transaction_count == 0:
            self.connection.commit()

    def _create_tables(self) -> None:
        with self.connection as conn:
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
        with self.connection as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (title, description, due_date, due_time)
                VALUES (?, ?, ?, ?)
            """, (title, description, due_date, due_time))
            conn.commit()
            return cursor.lastrowid or 0
    
    @lru_cache(maxsize=100)
    def get_tasks_for_date(self, date: str) -> List[Dict[str, Any]]:
        cursor = self.connection.execute(
            "SELECT * FROM tasks WHERE due_date = ? ORDER BY due_time",
            (date,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def update_task(self, task_id: int, **kwargs) -> bool:
        valid_fields = {'title', 'description', 'due_date', 'due_time', 'completed','in_progress'}
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not update_fields:
            return False
        
        set_clause = ", ".join(f"{k} = ?" for k in update_fields)
        values = list(update_fields.values())
        values.append(task_id)
        
        batch = kwargs.pop('batch', False)
        if batch:
            self.begin_transaction()
        
        try:
            self.connection.execute(f"""
                UPDATE tasks 
                SET {set_clause}
                WHERE id = ?
            """, values)
            
            if not batch:
                self.connection.commit()
            else:
                self.commit_transaction()
                
            self.get_tasks_for_date.cache_clear()
            return task_id
            
        except Exception as e:
            self.connection.rollback()
            raise e
    
    def delete_task(self, task_id: int) -> bool:
        with self.connection as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def save_notes(self, date: str, content: str) -> bool:
        with self.connection as conn:
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
        with self.connection as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM notes WHERE date = ?", (date,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_tasks_between_dates(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        with self.connection as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE due_date BETWEEN ? AND ?
                ORDER BY due_date, due_time
            """, (start_date, end_date))
            
            return [dict(row) for row in cursor.fetchall()]

    def get_upcoming_tasks(self, start_date: str, days: int = 7) -> List[Dict[str, Any]]:
        with self.connection as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE due_date > ? AND due_date <= date(?, '+' || ? || ' days')
                ORDER BY due_date, due_time
            """, (start_date, start_date, days))
            return [dict(row) for row in cursor.fetchall()]
