import datetime
from typing import Dict, List, Optional

class Assignment:
    def __init__(self, name: str):
        self.name = name
        self.completed = False

    def __str__(self):
        status = "[X]" if self.completed else "[ ]"
        return f"{status} {self.name}"

    def toggle_completion(self):
        self.completed = not self.completed

class Week:
    def __init__(self, week_number: int):
        self.week_number = week_number
        self.assignments: List[List[Assignment]] = [[] for _ in range(7)]

    def add_assignment(self, day: int, name: str):
        self.assignments[day].append(Assignment(name))

    def toggle_assignment_completion(self, day: int, assignment_index: int):
        if 0 <= day < 7 and 0 <= assignment_index < len(self.assignments[day]):
            self.assignments[day][assignment_index].toggle_completion()

class Semester:
    def __init__(self, name: str, start_date: datetime.date):
        self.name = name
        self.start_date = start_date
        self.weeks: Dict[int, Week] = {}

    def enter_week(self, week_number: int) -> Week:
        if week_number not in self.weeks:
            self.weeks[week_number] = Week(week_number)
        return self.weeks[week_number]

class ClassSchedule:
    def __init__(self):
        self.semesters: Dict[str, Semester] = {}

    def add_semester(self, name: str, start_date: datetime.date):
        self.semesters[name] = Semester(name, start_date)

    def view_schedule(self) -> List[str]:
        return list(self.semesters.keys())
