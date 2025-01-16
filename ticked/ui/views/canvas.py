import asyncio
from asyncio import to_thread
from typing import List, Dict
import json
from pathlib import Path
from datetime import datetime
from canvasapi import Canvas
from textual.widgets import DataTable, Static, LoadingIndicator, Button, Input
from textual.containers import Vertical, Grid
from textual.app import ComposeResult
from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message

class CanvasLoginMessage(Message):
    def __init__(self, url: str, token: str) -> None:
        self.url = url
        self.token = token
        super().__init__()

class CanvasLogin(Widget):
    class Submitted(Message):
        pass

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("Canvas Login", classes="header"),
            Static("Enter your Canvas URL and API token to sync your courses.", classes="description"),
            Input(placeholder="Canvas URL (e.g., https://canvas.university.edu)", id="url"),
            Input(placeholder="API Token", id="token", password=True),
            Static("How to get your API token and sync your courses:", classes="help1"),
            Static("1. Log into your Canvas account through your University", classes="help"),
            Static("2. Go to Account -> Settings", classes="help"),
            Static("3. Look for 'Approved Integrations' and select '+ New Access Token'", classes="help"),
            Static("4. Copy and paste the access token into the input above \n   and be sure to paste the link to your Universities Canvas site above \n   (i.e., https://canvas.college.edu)", classes="help"),
            Button("Login", variant="primary", id="login"),
            classes="login-container"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login":
            url_input = self.query_one("#url", Input)
            token_input = self.query_one("#token", Input)
            if url_input.value and token_input.value:
                self.save_credentials(url_input.value, token_input.value)
                self.post_message(CanvasLoginMessage(url_input.value, token_input.value))
            else:
                self.notify("Please enter both URL and API token", severity="error")

    def load_credentials(self) -> tuple[str, str]:
        config_path = Path.home() / ".canvas_config.json"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    return data.get("url", ""), data.get("token", "")
            except:
                return "", ""
        return "", ""

    def save_credentials(self, url: str, token: str) -> None:
        config_path = Path.home() / ".canvas_config.json"
        try:
            with open(config_path, "w") as f:
                json.dump({"url": url, "token": token}, f)
        except Exception as e:
            self.notify(f"Failed to save credentials: {str(e)}", severity="error")

class CanvasAPI:
    def __init__(self):
        self.canvas = None

    def get_courses(self) -> List[Dict]:
        courses = []
        try:
            for course in self.canvas.get_courses(
                enrollment_type="student",
                include=["total_scores", "current_grading_period_scores", "grades"],
                state=["available"],
            ):
                code = getattr(course, "course_code", "")
                if code and "2501" in str(code):
                    if hasattr(course, "enrollments") and course.enrollments:
                        e = course.enrollments[0]
                        l = e.get("computed_current_letter_grade") or e.get("computed_current_grade")
                        p = e.get("computed_current_score")
                        if l and p is not None:
                            g = f"{l} ({p}%)"
                        elif l:
                            g = l
                        elif p is not None:
                            g = f"{p}%"
                        else:
                            g = "N/A"
                        n = getattr(course, "name", "Unnamed Course")
                        c = getattr(course, "course_code", "No Code")
                        courses.append({"name": n, "code": c, "grade": g})
        except Exception as e:
            print(f"Error in get_courses: {str(e)}")
            raise e
        return courses

    def get_todo_assignments(self) -> List[Dict]:
        assignments = []
        try:
            for course in self.canvas.get_courses(enrollment_type="student", state=["available"]):
                code = getattr(course, "course_code", "")
                if code and "2501" in str(code):
                    for a in course.get_assignments(bucket="upcoming", include=["submission"]):
                        if hasattr(a, "due_at") and a.due_at:
                            d = datetime.strptime(a.due_at, "%Y-%m-%dT%H:%M:%SZ")
                            if d > datetime.now():
                                s = "Not Started"
                                if hasattr(a, "submission") and a.submission:
                                    if a.submission.get("submitted_at"):
                                        s = "Submitted"
                                    elif a.submission.get("missing"):
                                        s = "Missing"
                                assignments.append({
                                    "name": a.name,
                                    "course": course.name,
                                    "due_date": d.strftime("%Y-%m-%d %H:%M"),
                                    "status": s
                                })
            for x in assignments:
                if x["due_date"] != "No Due Date":
                    dt = datetime.strptime(x["due_date"], "%Y-%m-%d %H:%M")
                    x["due_date"] = dt.strftime("%B %d - %H:%M")
            assignments.sort(key=lambda x: datetime.strptime(x["due_date"], "%B %d - %H:%M") if x["due_date"] != "No Due Date" else datetime.max)
        except Exception as e:
            print(f"Error in get_todo_assignments: {str(e)}")
            raise e
        return assignments

class CourseList(DataTable):
    def __init__(self):
        super().__init__()
        self.cursor_type = "row"
        self.add_columns("Name", "Code", "Current Grade")

    def populate(self, courses: List[Dict]):
        self.clear()
        for c in courses:
            self.add_row(c.get("name", "Unnamed Course"), c.get("code", "No Code"), c.get("grade", "N/A"))

class TodoList(DataTable):
    def __init__(self):
        super().__init__()
        self.cursor_type = "row"
        self.add_columns("Assignment", "Course", "Due Date", "Status")

    def populate(self, assignments: List[Dict]):
        self.clear()
        for a in assignments:
            self.add_row(a.get("name", "Unnamed Assignment"), a.get("course", "Unknown Course"), a.get("due_date", "No Due Date"), a.get("status", "Not Started"))

class CanvasView(Widget):
    selected_course_id = reactive(None)

    def __init__(self):
        super().__init__()
        self.canvas_api = None
        self.is_authenticated = False

    async def test_connection(self) -> bool:
        try:
            user = self.canvas_api.canvas.get_current_user()
            return True
        except Exception as e:
            self.notify(f"Canvas API Connection Error: {str(e)}", severity="error")
            print(f"Canvas API Connection Error: {str(e)}")
            return False

    def compose(self) -> ComposeResult:
        yield CanvasLogin()
        with Grid(id="canvas-grid", classes="hidden"):
            with Vertical(id="left-panel"):
                yield Static("Current Courses", classes="header")
                yield CourseList()
                yield Static("Upcoming Assignments", classes="header")
                yield TodoList()
            with Vertical(id="right-panel"):
                yield LoadingIndicator()
                yield Button("Refresh", id="refresh")

    def on_mount(self) -> None:
        login = self.query_one(CanvasLogin)
        url, token = login.load_credentials()
        if url and token:
            self.initialize_canvas(url, token)

    def on_canvas_login_message(self, message: CanvasLoginMessage) -> None:
        self.initialize_canvas(message.url, message.token)

    def initialize_canvas(self, url: str, token: str) -> None:
        self.canvas_api = CanvasAPI()
        self.canvas_api.canvas = Canvas(url, token)
        asyncio.create_task(self._initialize())

    async def _initialize(self) -> None:
        if await self.test_connection():
            self.query_one("#canvas-grid").remove_class("hidden")
            self.query_one(CanvasLogin).remove()
            self.is_authenticated = True
            await self.load_data()
        else:
            self.query_one(LoadingIndicator).styles.display = "none"

    async def load_data(self) -> None:
        try:
            self.query_one(LoadingIndicator).styles.display = "block"
            c_task = asyncio.to_thread(self.canvas_api.get_courses)
            t_task = asyncio.to_thread(self.canvas_api.get_todo_assignments)
            courses, todos = await asyncio.gather(c_task, t_task)
            self.query_one(CourseList).populate(courses)
            self.query_one(TodoList).populate(todos)
        except Exception as e:
            self.notify(f"Error loading data: {str(e)}", severity="error")
            print(f"Canvas API Error: {str(e)}")
        finally:
            self.query_one(LoadingIndicator).styles.display = "none"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            asyncio.create_task(self.load_data())
