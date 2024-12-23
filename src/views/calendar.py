from textual.containers import Container, Grid, Horizontal
from textual.widgets import Button, Static
from textual.app import ComposeResult
from datetime import datetime
import calendar

class NavBar(Horizontal):
    """Navigation bar container with month controls."""
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
        header.styles.margin = (0, 4)
        
        yield prev_btn
        yield header
        yield next_btn

class CalendarDayButton(Button):
    """A custom button for calendar days."""
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
    """Header showing current month and year."""
    def __init__(self, current_date: datetime):
        super().__init__(f"{current_date.strftime('%B %Y')}")
        self.styles.text_align = "center"
        self.styles.width = "100%"
        self.styles.text_style = "bold"

class CalendarGrid(Grid):
    """Grid container for the calendar."""
    def __init__(self, current_date: datetime = None):
        super().__init__()
        self.current_date = current_date or datetime.now()
        self.styles.height = "85%"
        self.styles.width = "100%"
        self.styles.grid_size_rows = 7
        self.styles.grid_size_columns = 7
        self.styles.grid_gutter = 1
        self.styles.padding = 1
        
    def compose(self) -> ComposeResult:
        # Add weekday headers
        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for day in weekdays:
            header = Static(day, classes="calendar-weekday")
            header.styles.width = "100%"
            header.styles.height = "100%"
            header.styles.content_align = ("center", "middle")
            yield header
            
        # Calculate calendar days
        month_calendar = calendar.monthcalendar(
            self.current_date.year,
            self.current_date.month
        )
        
        # Add calendar days
        today = datetime.now().day
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        for week in month_calendar:
            for day in week:
                if day == 0:
                    empty_day = Static("", classes="calendar-empty-day")
                    empty_day.styles.width = "100%"
                    empty_day.styles.height = "100%"
                    yield empty_day
                else:
                    is_current = (day == today and
                                self.current_date.month == current_month and
                                self.current_date.year == current_year)
                    day_btn = CalendarDayButton(day, is_current)
                    yield day_btn

# calendar.py
# (Previous imports and classes remain the same until CalendarView)

class CalendarView(Container):
    """Main calendar view."""
    def __init__(self):
        super().__init__()
        self.current_date = datetime.now()
        self.styles.width = "100%"
        self.styles.height = "100%"
        self.styles.padding = (2, 4)
    
    def compose(self) -> ComposeResult:
        """Initial composition of the view."""
        yield NavBar(self.current_date)
        yield CalendarGrid(self.current_date)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        if button_id == "prev_month":
            if self.current_date.month == 1:
                self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
            else:
                self.current_date = self.current_date.replace(month=self.current_date.month - 1)
            self.refresh_calendar()
        elif button_id == "next_month":
            if self.current_date.month == 12:
                self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
            else:
                self.current_date = self.current_date.replace(month=self.current_date.month + 1)
            self.refresh_calendar()
        elif isinstance(event.button, CalendarDayButton):
            self.notify(f"Selected {self.current_date.strftime('%B')} {event.button.day}, {self.current_date.year}")
            
    def refresh_calendar(self) -> None:
        """Refresh the calendar view while maintaining the navbar."""
        # Update the header text
        navbar = self.query_one(NavBar)
        header = navbar.query_one(CalendarHeader)
        header.update(f"{self.current_date.strftime('%B %Y')}")
        
        # Remove old grid and mount new one
        try:
            old_grid = self.query_one(CalendarGrid)
            old_grid.remove()
        except Exception:
            pass  # In case grid doesn't exist
            
        new_grid = CalendarGrid(self.current_date)
        self.mount(new_grid)  # This will append it after the NavBar
