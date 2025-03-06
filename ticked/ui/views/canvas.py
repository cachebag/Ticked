import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup
from canvasapi import Canvas
from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import NoMatches, Widget
from textual.widgets import Button, DataTable, Input, LoadingIndicator, Markdown, Static


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
            Static(
                "Enter your Canvas URL and API token to sync your courses.",
                classes="description",
            ),
            Input(
                placeholder="Canvas URL (e.g., https://canvas.university.edu)", id="url"
            ),
            Input(placeholder="API Token", id="token", password=True),
            Static("How to get your API token and sync your courses:", classes="help1"),
            Static(
                "1. Log into your Canvas account through your University",
                classes="help",
            ),
            Static("2. Go to Account -> Settings", classes="help"),
            Static(
                "3. Look for 'Approved Integrations' and select '+ New Access Token'",
                classes="help",
            ),
            Static(
                "4. Copy and paste the access token into the input above \n   and be sure to paste the link to your Universities Canvas site above \n   (i.e., https://canvas.college.edu)",
                classes="help",
            ),
            Button("Login", variant="primary", id="login"),
            classes="login-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login":
            url_input = self.query_one("#url", Input)
            token_input = self.query_one("#token", Input)
            if url_input.value and token_input.value:
                self.save_credentials(url_input.value, token_input.value)
                self.post_message(
                    CanvasLoginMessage(url_input.value, token_input.value)
                )
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


class AnnouncementsList(Markdown):
    """
    This class turns a list of announcements into a single Markdown string
    and updates the Markdown widget accordingly.
    """

    def __init__(self) -> None:
        super().__init__("")
        self.auto_scroll = True

    def clean_html(self, html_content: str) -> str:
        """Convert basic HTML to plain text (inserting newlines for <br>, <p>, <div>, etc.)."""
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, "html.parser")

        for tag in soup.find_all(["br", "p", "div"]):
            tag.replace_with("\n" + tag.get_text() + "\n")

        text = soup.get_text()

        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r"^\s+|\s+$", "", text)
        return text

    def wrap_text(self, text: str, width: int = 80) -> str:
        """
        Wrap text to fit within specified width.
        This is optional if you want to limit line length in the Markdown display.
        """
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)

        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines)

    def populate(self, announcements: List[Dict]) -> None:
        """
        Convert all announcements into a single Markdown string, then update
        this Markdown widget to render them.
        """
        markdown_str = ""

        for announcement in announcements:
            title = announcement.get("title", "Untitled")
            html_message = announcement.get("message", "No content")
            posted_at = announcement.get("posted_at", "")
            course_name = announcement.get("course_name", "Unknown Course")

            cleaned_message = self.clean_html(html_message)
            wrapped_message = self.wrap_text(cleaned_message, width=80)

            if posted_at:
                try:
                    dt = datetime.strptime(posted_at, "%Y-%m-%dT%H:%M:%SZ")
                    posted_at = dt.strftime("%B %d, %Y")
                except:
                    posted_at = "Unknown date"

            markdown_str += f"# {title}\n\n"
            markdown_str += f"**Posted on:** {posted_at}\n\n"
            markdown_str += f"**Course:** {course_name}\n\n"

            markdown_str += "## Announcement\n\n"
            markdown_str += f"{wrapped_message}\n\n"

            markdown_str += "---\n\n"

        self.update(markdown_str)


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
                        enrollment = course.enrollments[0]
                        grade = enrollment.get(
                            "computed_current_letter_grade"
                        ) or enrollment.get("computed_current_grade")
                        p = enrollment.get("computed_current_score")
                        if grade and p is not None:
                            g = f"{grade} ({p}%)"
                        elif grade:
                            g = grade
                        elif p is not None:
                            g = f"{p}%"
                        else:
                            g = "N/A"
                        n = getattr(course, "name", "Unnamed Course")
                        c = getattr(course, "course_code", "No Code")
                        courses.append(
                            {
                                "name": f"{n:<40}",
                                "code": f"{c:<20}",
                                "grade": f"{g:>46}",
                            }
                        )
        except Exception as e:
            print(f"Error in get_courses: {str(e)}")
            raise e
        return courses

    def get_todo_assignments(self) -> List[Dict]:
        assignments = []
        try:
            for course in self.canvas.get_courses(
                enrollment_type="student", state=["available"]
            ):
                code = getattr(course, "course_code", "")
                if code and "2501" in str(code):
                    for a in course.get_assignments(
                        bucket="upcoming", include=["submission"]
                    ):
                        if hasattr(a, "due_at") and a.due_at:
                            d = datetime.strptime(a.due_at, "%Y-%m-%dT%H:%M:%SZ")
                            if d > datetime.now():
                                s = "Not Started"
                                if hasattr(a, "submission") and a.submission:
                                    if a.submission.get("submitted_at"):
                                        s = "Submitted"
                                    elif a.submission.get("missing"):
                                        s = "Missing"
                                assignments.append(
                                    {
                                        "name": a.name,
                                        "course": course.name,
                                        "due_date": d.strftime("%Y-%m-%d %H:%M"),
                                        "status": s,
                                    }
                                )
            for x in assignments:
                if x["due_date"] != "No Due Date":
                    dt = datetime.strptime(x["due_date"], "%Y-%m-%d %H:%M")
                    x["due_date"] = dt.strftime("%B %d - %H:%M")
            assignments.sort(
                key=lambda x: (
                    datetime.strptime(x["due_date"], "%B %d - %H:%M")
                    if x["due_date"] != "No Due Date"
                    else datetime.max
                )
            )
        except Exception as e:
            print(f"Error in get_todo_assignments: {str(e)}")
            raise e
        return assignments

    def get_announcements(self) -> List[Dict]:
        announcements = []
        cutoff_date = datetime(2025, 1, 1)
        try:
            for course in self.canvas.get_courses(
                enrollment_type="student", state=["available"]
            ):
                code = getattr(course, "course_code", "")
                if code and "2501" in str(code):
                    for announcement in course.get_discussion_topics(
                        only_announcements=True
                    ):
                        if announcement.posted_at:
                            posted_date = datetime.strptime(
                                announcement.posted_at, "%Y-%m-%dT%H:%M:%SZ"
                            )
                            if posted_date >= cutoff_date:
                                announcements.append(
                                    {
                                        "title": announcement.title,
                                        "message": announcement.message,
                                        "posted_at": announcement.posted_at,
                                        "course_name": course.name,
                                    }
                                )
            announcements.sort(
                key=lambda x: (
                    datetime.strptime(x["posted_at"], "%Y-%m-%dT%H:%M:%SZ")
                    if x["posted_at"]
                    else datetime.min
                ),
                reverse=True,
            )
        except Exception as e:
            print(f"Error in get_announcements: {str(e)}")
            raise e
        return announcements


class CourseList(DataTable):
    def __init__(self):
        super().__init__()
        self.cursor_type = "row"
        self.add_columns(
            "Name", "Code", "                                  Current Grade"
        )

    def populate(self, courses: List[Dict]):
        self.clear()
        for c in courses:
            self.add_row(
                c.get("name", "Unnamed Course"),
                c.get("code", "No Code"),
                c.get("grade", "N/A"),
            )


class TodoList(DataTable):
    def __init__(self):
        super().__init__()
        self.cursor_type = "row"
        self.add_columns("Assignment", "Course", "Due Date", "Status")

    def populate(self, assignments: List[Dict]):
        self.clear()
        for a in assignments:
            self.add_row(
                a.get("name", "Unnamed Assignment"),
                a.get("course", "Unknown Course"),
                a.get("due_date", "No Due Date"),
                a.get("status", "Not Started"),
            )


class CanvasView(Widget):
    selected_course_id = reactive(None)

    def __init__(self):
        super().__init__()
        self.canvas_api = None
        self.is_authenticated = False
        self.cache_dir = (
            Path.home() / ".canvas_cache"
        )  # caching loaded data to prevent persistent loading
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_path(self, cache_type: str) -> Path:
        return self.cache_dir / f"{cache_type}.json"

    def _save_cache(self, data: dict, cache_type: str) -> None:
        try:
            cache_data = {"timestamp": datetime.now().isoformat(), "data": data}
            with open(self._get_cache_path(cache_type), "w") as f:
                json.dump(cache_data, f)
        except Exception as e:
            print(f"Error saving cache for {cache_type}: {e}")

    def _load_cache(self, cache_type: str) -> tuple[list, datetime]:
        try:
            cache_path = self._get_cache_path(cache_type)
            if cache_path.exists():
                with open(cache_path, "r") as f:
                    cache_data = json.load(f)
                    timestamp = datetime.fromisoformat(cache_data["timestamp"])
                    return cache_data["data"], timestamp
        except Exception as e:
            print(f"Error loading cache for {cache_type}: {e}")
        return [], None

    async def _load_cached_data(self) -> None:
        try:
            courses, courses_time = self._load_cache("courses")
            todos, todos_time = self._load_cache("todos")
            announcements, announcements_time = self._load_cache("announcements")

            if courses:
                course_list = self.query_one("CourseList")  # Use string selector
                if course_list:
                    course_list.populate(courses)
            if todos:
                todo_list = self.query_one("TodoList")
                if todo_list:
                    todo_list.populate(todos)
            if announcements:
                announcements_list = self.query_one(AnnouncementsList)
                if announcements_list:
                    announcements_list.populate(announcements)

        except Exception as e:
            print(f"Error loading cached data: {e}")
            self.notify(f"Error loading cached data: {e}", severity="error")

    async def load_data(self) -> None:
        try:
            try:
                self.query_one(LoadingIndicator).styles.display = "block"
            except NoMatches:
                pass

            # First load cached data
            await self._load_cached_data()

            # Then fetch fresh data
            c_task = asyncio.to_thread(self.canvas_api.get_courses)
            t_task = asyncio.to_thread(self.canvas_api.get_todo_assignments)
            a_task = asyncio.to_thread(self.canvas_api.get_announcements)

            courses, todos, announcements = await asyncio.gather(c_task, t_task, a_task)

            # Update UI with fresh data
            self.query_one(CourseList).populate(courses)
            self.query_one(TodoList).populate(todos)
            self.query_one(AnnouncementsList).populate(announcements)

            # Save to cache
            self._save_cache(courses, "courses")
            self._save_cache(todos, "todos")
            self._save_cache(announcements, "announcements")

        except Exception as e:
            self.notify(f"Error loading data: {str(e)}", severity="error")
            print(f"Canvas API Error: {str(e)}")
        finally:
            try:
                self.query_one(LoadingIndicator).styles.display = "block"
            except NoMatches:
                pass

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
                yield Static("Recent Announcements", classes="headerA")
                yield AnnouncementsList()
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
            try:
                self.query_one(LoadingIndicator).styles.display = "block"
            except NoMatches:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            asyncio.create_task(self.load_data())
