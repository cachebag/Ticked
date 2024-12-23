from textual.containers import Container, Grid, Horizontal
from textual.widgets import Button, Static
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
        self.styles.grid_gutter = 1
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
            self.notify(f"Selected {self.current_date.strftime('%B')} {event.button.day}, {self.current_date.year}")
    
    def _refresh_calendar(self) -> None:
        self.query("NavBar").first().remove()
        self.query("CalendarGrid").first().remove()
        
        self.mount(NavBar(self.current_date))
        self.mount(CalendarGrid(self.current_date))
