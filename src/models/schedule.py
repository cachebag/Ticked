# src/models/schedule.py
import datetime
from typing import Dict, List
from .semester import Semester

class ClassSchedule:
    def __init__(self):
        self.semesters: Dict[str, Semester] = {}

    def add_semester(self, name: str, start_date: datetime.date):
        self.semesters[name] = Semester(name, start_date)

    def view_schedule(self) -> List[str]:
        return list(self.semesters.keys())
