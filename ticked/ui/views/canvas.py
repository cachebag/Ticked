# canvas_view.py
from textual.widgets import DataTable, Static, LoadingIndicator, Button
from textual.containers import Horizontal, Vertical
from textual.app import ComposeResult
from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
import os
from dotenv import load_dotenv
from canvasapi import Canvas
from datetime import datetime
import asyncio
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

class CanvasAPI:
    def __init__(self):
        self.canvas = Canvas(
            os.getenv("CANVAS_API_URL"),
            os.getenv("CANVAS_API_TOKEN")
        )
    
    async def get_courses(self) -> List[Dict]:
        """Fetch all active courses"""
        courses = []
        for course in self.canvas.get_courses(enrollment_state='active'):
            courses.append({
                'id': course.id,
                'name': course.name,
                'code': course.course_code,
                'start_date': getattr(course, 'start_at', 'N/A')
            })
        return courses
    
    async def get_assignments(self, course_id: int) -> List[Dict]:
        """Fetch assignments for a specific course"""
        course = self.canvas.get_course(course_id)
        assignments = []
        for assignment in course.get_assignments():
            assignments.append({
                'id': assignment.id,
                'name': assignment.name,
                'due_date': getattr(assignment, 'due_at', 'N/A'),
                'points': assignment.points_possible
            })
        return assignments

    async def get_announcements(self, course_id: int) -> List[Dict]:
        """Fetch announcements for a specific course"""
        course = self.canvas.get_course(course_id)
        announcements = []
        for announcement in course.get_announcements():
            announcements.append({
                'id': announcement.id,
                'title': announcement.title,
                'posted': announcement.posted_at,
                'message': announcement.message
            })
        return announcements

class CourseList(DataTable):
    def __init__(self):
        super().__init__()
        self.cursor_type = "row"
        self.add_columns("ID", "Name", "Code", "Start Date")

    def populate(self, courses: List[Dict]):
        self.clear()
        for course in courses:
            # Ensure we have a valid ID
            course_id = str(course.get('id', ''))
            if course_id:
                self.add_row(
                    course_id,
                    course.get('name', 'Unnamed Course'),
                    course.get('code', 'No Code'),
                    course.get('start_date', 'N/A'),
                    key=course_id  # Explicitly set the row key
                )

class AssignmentList(DataTable):
    def __init__(self):
        super().__init__()
        self.cursor_type = "row"
        self.add_columns("Name", "Due Date", "Points")

    def populate(self, assignments: List[Dict]):
        self.clear()
        for assignment in assignments:
            self.add_row(
                assignment['name'],
                assignment['due_date'],
                str(assignment['points'])
            )

class AnnouncementList(Static):
    def __init__(self):
        super().__init__()
        self.announcements: List[Dict] = []

    def populate(self, announcements: List[Dict]):
        self.announcements = announcements
        content = ""
        for announcement in announcements:
            content += f"\n# {announcement['title']}\n"
            content += f"Posted: {announcement['posted']}\n"
            content += f"{announcement['message']}\n"
            content += "-" * 50 + "\n"
        self.update(content)

class CanvasView(Widget):
    selected_course_id = reactive(None)
    
    def __init__(self):
        super().__init__()
        self.canvas_api = CanvasAPI()
        
    async def test_connection(self) -> bool:
        try:
            # Try to get current user as a connection test
            user = self.canvas_api.canvas.get_current_user()
            return True
        except Exception as e:
            self.notify(f"Canvas API Connection Error: {str(e)}", severity="error")
            print(f"Canvas API Connection Error: {str(e)}")  # For debugging
            return False

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()
        yield Button("Refresh", id="refresh")
        with Horizontal():
            with Vertical():
                yield Static("Courses", classes="header")
                yield CourseList()
            with Vertical():
                yield Static("Assignments", classes="header")
                yield AssignmentList()
        with Vertical():
            yield Static("Announcements", classes="header")
            yield AnnouncementList()

    def on_mount(self) -> None:
        asyncio.create_task(self._initialize())
        
    async def _initialize(self) -> None:
        if await self.test_connection():
            await self.load_courses()
        else:
            self.query_one(LoadingIndicator).styles.display = "none"

    async def load_courses(self) -> None:
        try:
            self.query_one(LoadingIndicator).styles.display = "block"
            courses = await self.canvas_api.get_courses()
            self.query_one(CourseList).populate(courses)
        except Exception as e:
            self.notify(f"Error loading courses: {str(e)}", severity="error")
            print(f"Canvas API Error: {str(e)}")  # For debugging
        finally:
            self.query_one(LoadingIndicator).styles.display = "none"

    async def load_assignments(self) -> None:
        if self.selected_course_id:
            try:
                print(f"Loading assignments for course {self.selected_course_id}")
                assignments = await self.canvas_api.get_assignments(self.selected_course_id)
                print(f"Found {len(assignments)} assignments")
                self.query_one(AssignmentList).populate(assignments)
            except Exception as e:
                self.notify(f"Error loading assignments: {str(e)}", severity="error")
                print(f"Error loading assignments: {str(e)}")

    async def load_announcements(self) -> None:
        if self.selected_course_id:
            announcements = await self.canvas_api.get_announcements(self.selected_course_id)
            self.query_one(AnnouncementList).populate(announcements)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if isinstance(event.data_table, CourseList):
            try:
                # Get the selected row data directly
                row_data = event.data_table.get_row_at(event.cursor_row)
                if row_data and len(row_data) > 0:
                    course_id = int(row_data[0])  # First column contains the ID
                    self.selected_course_id = course_id
                    asyncio.create_task(self.load_assignments())
                    asyncio.create_task(self.load_announcements())
                else:
                    self.notify("Could not get course ID from selected row", severity="error")
            except (ValueError, TypeError, IndexError) as e:
                self.notify(f"Error selecting course: {str(e)}", severity="error")
                print(f"Error in course selection: {str(e)}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            asyncio.create_task(self.load_courses())
            if self.selected_course_id:
                asyncio.create_task(self.load_assignments())
                asyncio.create_task(self.load_announcements())

# CSS styles for the Canvas View
CANVAS_VIEW_CSS = """
CanvasView {
    height: 100%;
    padding: 1;
}

.header {
    dock: top;
    padding: 1;
    background: $accent;
    color: $text;
    text-align: center;
    text-style: bold;
}

DataTable {
    height: 50%;
    border: solid $accent;
}

Static {
    background: $surface;
    color: $text;
    padding: 1;
}

Button {
    dock: top;
    width: auto;
    margin: 1;
}

LoadingIndicator {
    align: center middle;
}
"""