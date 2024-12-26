from textual.containers import Container, Grid, Horizontal, Vertical
from textual.widgets import Button, Static, TextArea
from textual.widgets.markdown import Markdown
from textual.app import ComposeResult
from datetime import datetime
import calendar

class NavBar(Horizontal):
    def __init__(self, current_date: datetime):
        super().__init__()
        self.current_date = current_date
        self.styles.width = "100%"
        self.styles.height = "5"
        self.styles.align = ("center", "middle")

    def compose(self) -> ComposeResult:
        prev_btn = Button("◄", id="prev_month", classes="calendar-nav-left")
        next_btn = Button("►", id="next_month", classes="calendar-nav-right")
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
    def __init__(self, current_date: datetime = None):
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
            day_view.date = selected_date
            day_view.styles.display = "block"  
            self.query_one(CalendarGrid).styles.display = "none"  
            self.query_one(NavBar).styles.display = "none"
            header = self.query_one("#day-view-header")
            header.update(f"Schedule for {selected_date.strftime('%B %d, %Y')}")
            event.stop()


    def action_back_to_calendar(self) -> None:
        self.query_one(DayView).styles.display = "none"
        self.query_one(CalendarGrid).styles.display = "block"
        self.query_one(NavBar).styles.display = "block"  
    
    def _refresh_calendar(self) -> None:
        self.query("NavBar").first().remove()
        self.query("CalendarGrid").first().remove()
        
        self.mount(NavBar(self.current_date))
        self.mount(CalendarGrid(self.current_date))

class ScheduleSection(Vertical):
   # TODO: Implement task addition 
    def compose(self) -> ComposeResult:
        yield Static("Schedule & Tasks", classes="section-header")
        with Horizontal(classes="schedule-controls"):
            yield Button("+ Add Task", id="add-task", classes="schedule-button")
        yield Static("Today's Tasks:", classes="task-header")
        with Vertical(classes="tasks-list"):
            yield Static("No tasks scheduled for today", classes="empty-schedule")

class NotesSection(Vertical):
    def __init__(self):
        super().__init__()
        self.notes_content = """# Notes
Start writing your notes here...

* Use markdown formatting
* Add lists and headers
* Your notes will render as you type"""
    
    def compose(self) -> ComposeResult:
        yield Static("Notes", classes="section-header")
        yield TextArea(self.notes_content, id="notes-editor")
        with Horizontal(classes="notes-controls"):
            yield Button("Save", id="save-notes", classes="notes-button")
    
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        text_area = self.query_one("#notes-editor", TextArea)
        text_area.styles.height = "1fr"  
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses for save and preview toggle."""
        if event.button.id == "save-notes":
            self.notify("Notes saved!", severity="success")
            # TODO: Implement actual save functionality
        elif event.button.id == "toggle-preview":
            preview_container = self.query_one(".preview-container")
            editor_container = self.query_one(".editor-container")
            
            if "hidden" in preview_container.classes:
                preview_container.remove_class("hidden")
                editor_container.styles.width = "50%"
            else:
                preview_container.add_class("hidden")
                editor_container.styles.width = "100%"


class DayView(Vertical):
    def __init__(self, date: datetime):
        super().__init__()
        self.date = date
    
    def compose(self) -> ComposeResult:
        yield Static(f"{self.date.strftime('%B %d, %Y')}", id="day-view-header")
        yield Button("Back to Calendar", id="back-to-calendar", classes="back-button")
        
        with Horizontal(classes="day-view-content"):
            with Container(classes="schedule-container"):
                yield ScheduleSection()
            with Container(classes="notes-container"):
                yield NotesSection()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-to-calendar":
            self.styles.display = "none"

    
