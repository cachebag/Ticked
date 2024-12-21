from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum, auto
from typing import Optional

class TaskType(Enum):
    ASSIGNMENT = auto()
    EXAM = auto()
    APPOINTMENT = auto()
    MEETING = auto()
    DEADLINE = auto()
    OTHER = auto()
    
    @classmethod
    def from_string(cls, value: str) -> 'TaskType':
        lookup = {
            'assignment': cls.ASSIGNMENT,
            'exam': cls.EXAM,
            'appointment': cls.APPOINTMENT,
            'meeting': cls.MEETING,
            'deadline': cls.DEADLINE,
            'other': cls.OTHER
        }
        return lookup.get(value.lower(), cls.OTHER)

@dataclass
class Task:
    title: str
    date: datetime
    task_type: TaskType
    time: Optional[time] = None
    description: Optional[str] = None
    
    def format_for_display(self) -> str:
        """Format task for display in calendar cell"""
        time_str = f"{self.time.strftime('%H:%M')} " if self.time else ""
        type_indicator = self.task_type.name[0]  # First letter of type
        return f"{time_str}{type_indicator}: {self.title}"
        
    @property
    def color_pair(self) -> int:
        """Return the appropriate color pair for this task type"""
        color_map = {
            TaskType.ASSIGNMENT: 1,  # Green
            TaskType.EXAM: 4,        # Red
            TaskType.APPOINTMENT: 5,  # Yellow
            TaskType.MEETING: 3,     # Default
            TaskType.DEADLINE: 4,    # Red
            TaskType.OTHER: 1,       # Green
        }
        return color_map.get(self.task_type, 1)
