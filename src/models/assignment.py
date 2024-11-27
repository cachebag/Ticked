class Assignment:
    def __init__(self, name: str):
        self.name = name
        self.completed = False

    def __str__(self):
        status = "[X]" if self.completed else "[ ]"
        return f"{status} {self.name}"

    def toggle_completion(self):
        self.completed = not self.completed
