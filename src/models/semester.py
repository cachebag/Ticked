# src/models/semester.py
import datetime
from typing import Dict
from .week import Week

class Semester:
    def __init__(self, name: str, start_date: datetime.date):
        self.name = name
        self.start_date = start_date
        self.weeks: Dict[int, Week] = {}

    def enter_week(self, week_number: int) -> Week:
        if week_number not in self.weeks:
            self.weeks[week_number] = Week(week_number)
        return self.weeks[week_number]
