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
        time_str = self.time.strftime('%H:%M') if self.time else '--:--'
        
        if self.task_type in [TaskType.MEETING, TaskType.OTHER, TaskType.EXAM]:
            return f"{self.title} @ {time_str}"
        else:
            return f"{self.title} due at {time_str}"
    
    @property
    def color_pair(self) -> int:
        """Return the appropriate color pair based on Gruvbox-inspired theme"""
        color_map = {
            TaskType.ASSIGNMENT: 1,  # Soft Green
            TaskType.EXAM: 2,        # Soft Red
            TaskType.APPOINTMENT: 3,  # Soft Yellow
            TaskType.MEETING: 4,     # Soft Blue
            TaskType.DEADLINE: 5,    # Soft Purple
            TaskType.OTHER: 6,       # Soft Aqua
        }
        return color_map.get(self.task_type, 1)
