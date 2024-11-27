from typing import List
from .assignment import Assignment

class Week:
    def __init__(self, week_number: int):
        self.week_number = week_number
        self.assignments: List[List[Assignment]] = [[] for _ in range(7)]

    def add_assignment(self, day: int, name: str):
        self.assignments[day].append(Assignment(name))

    def toggle_assignment_completion(self, day: int, assignment_index: int):
        if 0 <= day < 7 and 0 <= assignment_index < len(self.assignments[day]):
            self.assignments[day][assignment_index].toggle_completion()
