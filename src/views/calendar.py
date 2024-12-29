from textual.containers import Container, Grid, Horizontal, Vertical
from textual.widgets import Button, Input, Label, Static, TextArea
from textual.screen import ModalScreen
from textual import on
from textual.app import ComposeResult
from datetime import datetime
import calendar
from .task_widget import Task

class NavBar(Horizontal):
    def __init__(self, current_date: datetime):
        super().__init__()
        self.current_date = current_date
        self.styles.width = "100%"
        self.styles.height = "5"
        self.styles.align = ("center", "middle")

    def compose(self) -> ComposeResult:
        prev_btn = Button("\u25C4 \n \n", id="prev_month", classes="calendar-nav-left")
        next_btn = Button("\u25BA", id="next_month", classes="calendar-nav-right")
        header = CalendarHeader(self.current_date)
        header.styles.width = "100%"
        header.styles.margin = (0, 5)

        yield prev_btn
        yield header
        yield next_btn

class CalendarDayButton(Button):
    def __init__(self, day: int, is_current: bool = False) -> None:
        super().__init__(str(day))
        self.day = day
        self.is_current = is_current
        self.styles.content_align = ("center", "middle")
        self.styles.width = "100%"
        self.styles.height = "100%"
        if is_current:
            self.add_class("current-day")

class CalendarHeader(Static):
    def __init__(self, current_date: datetime):
        month_year = current_date.strftime('%B %Y')
        super().__init__(month_year)
        self.styles.text_align = "center"
        self.styles.width = "100%"
        self.styles.text_style = "bold"

class CalendarGrid(Grid):
    def __init__(self, current_date: datetime | None = None):
        super().__init__()
        self.current_date = current_date or datetime.now()
        self.styles.height = "85%"
        self.styles.width = "100%"
        self.styles.grid_size_rows = 7
        self.styles.grid_size_columns = 7
        self.styles.padding = 1

    def compose(self) -> ComposeResult:
        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for day in weekdays:
            header = Static(day, classes="calendar-weekday")
            header.styles.width = "100%"
            header.styles.height = "100%"
            header.styles.content_align = ("center", "middle")
            yield header

        month_calendar = calendar.monthcalendar(
            self.current_date.year,
            self.current_date.month
        )

        today = datetime.now()

        for week in month_calendar:
            for day in week:
                if day == 0:
                    empty_day = Static("", classes="calendar-empty-day")
                    empty_day.styles.width = "100%"
                    empty_day.styles.height = "100%"
                    yield empty_day
                else:
                    is_current = (day == today.day and
                                self.current_date.month == today.month and
                                self.current_date.year == today.year)
                    day_btn = CalendarDayButton(day, is_current)
                    yield day_btn

class CalendarView(Container):
    def compose(self) -> ComposeResult:
        self.current_date = datetime.now()
        yield NavBar(self.current_date)
        yield CalendarGrid(self.current_date)
        yield DayView(self.current_date)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "prev_month":
            year = self.current_date.year
            month = self.current_date.month - 1
            if month < 1:
                year -= 1
                month = 12
            self.current_date = self.current_date.replace(year=year, month=month, day=1)
            self._refresh_calendar()
            event.stop()

        elif button_id == "next_month":
            year = self.current_date.year
            month = self.current_date.month + 1
            if month > 12:
                year += 1
                month = 1
            self.current_date = self.current_date.replace(year=year, month=month, day=1)
            self._refresh_calendar()
            event.stop()

        elif isinstance(event.button, CalendarDayButton):
            selected_date = self.current_date.replace(day=event.button.day)
            day_view = self.query_one(DayView)
            day_view.set_date(selected_date)

            self.query_one(CalendarGrid).styles.display = "none"
            self.query_one(NavBar).styles.display = "none"
            day_view.styles.display = "block"
            event.stop()

        elif button_id == "save_notes":
            day_view = self.query_one(DayView)
            event.stop()
            day_view.refresh_tasks()

        elif button_id == "add-task":
            event.stop()

        else:
            self.query_one(CalendarGrid).styles.display = "block"
            self.query_one(NavBar).styles.display = "block"
            self.query_one(DayView).styles.display = "none"
            self._refresh_calendar()
            event.stop()

    def action_back_to_calendar(self) -> None:
        day_view = self.query_one(DayView)
        day_view.styles.display = "none"
        self.query_one(CalendarGrid).styles.display = "block"
        self.query_one(NavBar).styles.display = "block"
        self._refresh_calendar()

    def _refresh_calendar(self) -> None:
        self.query("NavBar").first().remove()
        self.query("CalendarGrid").first().remove()
        self.mount(NavBar(self.current_date))
        self.mount(CalendarGrid(self.current_date))

class TaskForm(ModalScreen):
    def __init__(self, date: datetime) -> None:
        super().__init__()
        self.date = date

    def compose(self) -> ComposeResult:
        with Container(classes="task-form-container"):
            with Vertical(classes="task-form"):
                yield Static("Add New Task", classes="form-header")
                
                yield Static(f"Date: {self.date.strftime('%B %d, %Y')}", classes="selected-date")

                with Vertical():
                    yield Label("Title")
                    yield Input(placeholder="Enter task title", id="task-title")

                with Vertical():
                    yield Label("Due Time")
                    yield Input(placeholder="HH:MM", id="task-time")

                with Vertical():
                    yield Label("Description (optional)")
                    yield TextArea(id="task-description")

                with Horizontal(classes="form-buttons"):
                    yield Button("Cancel", variant="error", id="cancel")
                    yield Button("Add Task", variant="success", id="submit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "submit":
            self._submit_form()

    def _submit_form(self) -> None:
        title = self.query_one("#task-title", Input).value
        time = self.query_one("#task-time", Input).value
        description = self.query_one("#task-description", TextArea).text

        if not title or not time:
            self.notify("Title and Time are required", severity="error")
            return

        try:
            datetime.strptime(time, "%H:%M")
        except ValueError:
            self.notify("Invalid time format", severity="error")
            return

        date = self.date.strftime('%Y-%m-%d')

        task_id = self.app.db.add_task(
            title=title,
            due_date=date,
            due_time=time,
            description=description
        )

        task = {
            "id": task_id,
            "title": title,
            "due_date": date,
            "due_time": time,
            "description": description
        }

        self.dismiss(task)

        try:
            day_view = self.app.screen.query_one(DayView)
            if day_view:
                day_view.refresh_tasks()
                self.notify("Task added successfully!")
        except Exception:
            pass
            
        try:
            from .welcome import TodayContent
            today_content = self.app.screen.query_one(TodayContent)
            if today_content:
                today_content.refresh_tasks()
        except Exception:
            pass 

class TaskEditForm(TaskForm):
    def __init__(self, task_data: dict):
        super().__init__(date=datetime.strptime(task_data['due_date'], '%Y-%m-%d'))
        self.task_data = task_data

    def compose(self) -> ComposeResult:
        with Container(classes="task-form-container"):
            with Vertical(classes="task-form"):
                yield Static("Edit Task", classes="form-header")

                with Vertical():
                    yield Label("Title")
                    yield Input(value=self.task_data['title'], id="task-title")

                with Vertical():
                    yield Label("Due Time")
                    yield Input(value=self.task_data['due_time'], id="task-time")

                with Vertical():
                    yield Label("Description (optional)")
                    yield TextArea(self.task_data['description'], id="task-description")

                with Horizontal(classes="form-buttons"):
                    yield Button("Delete", variant="error", id="delete")
                    yield Button("Cancel", variant="primary", id="cancel")
                    yield Button("Save", variant="success", id="submit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            event.stop()
            # self.app.pop_screen() I'm not sure why but adding this breaks the screen
        elif event.button.id == "delete":
            self.app.db.delete_task(self.task_data['id'])
            self.dismiss(None)
            
            try:
                day_view = self.app.screen.query_one(DayView)
                if day_view:
                    day_view.refresh_tasks()
            except Exception:
                pass
                
            try:
                from .welcome import TodayContent
                today_content = self.app.screen.query_one(TodayContent)
                if today_content:
                    today_content.refresh_tasks()
            except Exception:
                pass
                
            self.notify("Task deleted successfully!")
            event.stop()
        elif event.button.id == "submit":
            self._submit_form()
            event.stop()

    def _submit_form(self) -> None:
        title = self.query_one("#task-title", Input).value
        time = self.query_one("#task-time", Input).value
        description = self.query_one("#task-description", TextArea).text

        if not title or not time:
            self.notify("Title and Time are required", severity="error")
            return

        try:
            datetime.strptime(time, "%H:%M")
        except ValueError:
            self.notify("Invalid time format", severity="error")
            return

        task_id = self.app.db.update_task(
            self.task_data['id'],
            title=title,
            due_date=self.date.strftime('%Y-%m-%d'),
            due_time=time,
            description=description
        )

        task = {
            "id": task_id,
            "title": title,
            "due_date": self.date.strftime('%Y-%m-%d'),
            "due_time": time,
            "description": description
        }

        self.dismiss(task)
        
        try:
            day_view = self.app.screen.query_one(DayView)
            if day_view:
                day_view.refresh_tasks()
                self.notify("Task updated successfully!")
        except Exception:
            pass
            
        try:
            from .welcome import TodayContent
            today_content = self.app.screen.query_one(TodayContent)
            if today_content:
                today_content.refresh_tasks()
        except Exception:
            pass
 

class ScheduleSection(Vertical):
    def __init__(self, date: datetime) -> None:
        super().__init__()
        self.date = date  

    def compose(self) -> ComposeResult:
        yield Static("Schedule & Tasks", classes="section-header")
        with Horizontal(classes="schedule-controls"):
            yield Button("+ Add Task", id="add-task", classes="schedule-button")
        yield Static("Today's Tasks:", classes="task-header")
        with Vertical(id="tasks-list", classes="tasks-list"):
            yield Static("No tasks scheduled for today", id="empty-schedule", classes="empty-schedule")

    @on(Button.Pressed, "#add-task")
    async def show_task_form(self, event: Button.Pressed) -> None:
        task_form = TaskForm(self.date)
        task = await self.app.push_screen(task_form)
       
        event.stop()

class NotesSection(Vertical):
    def __init__(self, date: datetime | None = None):
        super().__init__()
        self.date = date
        self.notes_content = "# Notes\nStart writing your notes here..."

    def compose(self) -> ComposeResult:
        yield Static("Notes", classes="section-header")
        yield TextArea(self.notes_content, id="notes-editor")
        with Horizontal(classes="notes-controls"):
            yield Button("Save", id="save-notes", classes="notes-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-notes":
            content = self.query_one("#notes-editor", TextArea).text
            if self.date:
                date_str = self.date.strftime('%Y-%m-%d')
                if self.app.db.save_notes(date_str, content):
                    self.notify(f"Notes saved for {date_str}!")
            else:
                self.notify("No date selected!", severity="error")
            event.stop()

class DayView(Vertical):
    def __init__(self, date: datetime):
        super().__init__()
        self.date = date
        self.styles.display = "none"

    def compose(self) -> ComposeResult:
        yield Static(f"{self.date.strftime('%B %d, %Y')}", id="day-view-header")
        yield Button("Back to Calendar", id="back-to-calendar", classes="back-button")

        with Horizontal(classes="day-view-content"):
            with Container(classes="schedule-container"):
                yield ScheduleSection(self.date)
            with Container(classes="notes-container"):
                yield NotesSection(self.date)

    def set_date(self, new_date: datetime) -> None:
        self.date = new_date
        self.query_one("#day-view-header").update(f"{self.date.strftime('%B %d, %Y')}")
        
        schedule_section = self.query_one(ScheduleSection)
        schedule_section.date = new_date
        
        notes_section = self.query_one(NotesSection)
        notes_section.date = new_date
        self.refresh_tasks()
        self.load_notes()

    def refresh_tasks(self) -> None:
        current_date = self.date.strftime('%Y-%m-%d')
        tasks = self.app.db.get_tasks_for_date(current_date)
        tasks_list = self.query_one("#tasks-list")

        tasks_list.remove_children()

        if tasks:
            for task in tasks:
                tasks_list.mount(Task(task))
        else:
            tasks_list.mount(Static("No tasks scheduled for today", classes="empty-schedule"))

    def load_notes(self) -> None:
        notes = self.app.db.get_notes(self.date.strftime('%Y-%m-%d'))
        notes_editor = self.query_one("#notes-editor", TextArea)
        if notes:
            notes_editor.text = notes
        else:
            notes_editor.text = "# Notes\nStart writing your notes here..."

