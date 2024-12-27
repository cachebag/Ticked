from textual.widgets import Static, TabPane, Button
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.app import ComposeResult
from datetime import datetime
from .calendar import Task
import requests
import random
import json

class TabButton(Button):
    def __init__(self, label: str, tab_id: str):
        super().__init__(label, id=f"tab_{tab_id}")
        self.tab_id = tab_id
        self.add_class("tab-button")
        
    def toggle_active(self, is_active: bool):
        if is_active:
            self.add_class("active")
        else:
            self.remove_class("active")

class ASCIIAnimation(Static):
    DEFAULT_CSS = """
    ASCIIAnimation {
        height: 100%;
        content-align: center middle;
        text-align: center;
    }
    """
    
    def __init__(self):
        super().__init__("")
        self.current_frame = 0
        self.frames = [
                ".",
    
                "|",
    
                "/",
    
                ]
    
    async def on_mount(self) -> None:
        self.update_animation()
    
    def update_animation(self) -> None:
        self.update(self.frames[self.current_frame])
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        self.set_timer(0.5, self.update_animation)

class DashboardCard(Container):
    def __init__(self, title: str, content: str = "", classes: str = None) -> None:
        super().__init__(classes=classes)
        self.title = title
        self.content = content
        self.add_class("dashboard-card")

    def compose(self) -> ComposeResult:
        yield Static(self.title, classes="card-title")
        yield Static(self.content, classes="card-content")

class TodayContent(Container):
    DEFAULT_CSS = """
    .dashboard-grid {
        grid-size: 2;
        grid-columns: 1fr 1fr;
        height: 100%;
        padding: 1;
        grid-gutter: 1;
    }
    
    .right-column {
        height: 100%;
        column-span: 1;
        grid-size: 2;
        grid-rows: 1fr 1fr;
        grid-gutter: 1;
    }
    
    .right-top-grid {
        grid-size: 2;
        grid-columns: 1fr 1fr;
        height: 100%;
        padding: 0;
        grid-gutter: 1;
    }
    
    .bottom-card {
        height: 100%;
        grid-size: 1;
        
    }
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.tasks_to_mount = None
    
    def fetch_and_cache_quotes(self):
        try:
            response = requests.get("https://zenquotes.io/api/quotes", timeout=10)
            if response.status_code == 200:
                quotes = response.json()
                with open("quotes_cache.json", "w") as file:
                    json.dump(quotes, file)
                print("Quotes cached successfully!")
            else:
                print(f"Failed to fetch quotes: {response.status_code}")
        except requests.RequestException as e:
            print(f"Error fetching quotes: {e}")


    def get_cached_quote(self):
        try:
            with open("quotes_cache.json", "r") as file:
                quotes = json.load(file)
                random_quote = random.choice(quotes)
                return f"{random_quote['q']} \n — {random_quote['a']}"
        except FileNotFoundError:
            self.fetch_and_cache_quotes()
            return "No quotes available. Please try again later."



    def compose(self) -> ComposeResult:
        with Grid(classes="dashboard-grid"):
            with Container(classes="tasks-card"):
                with DashboardCard("Today's Tasks"):
                    with Vertical(id="today-tasks-list", classes="tasks-list"):
                        yield Static("Loading tasks...", classes="empty-schedule")
            
            with Container(classes="right-column"):
                with Grid(classes="right-top-grid"):
                    quote = self.get_cached_quote()
                    yield DashboardCard("Quote of the Day", quote)
                    with DashboardCard("Nothing to see here yet"):
                        yield ASCIIAnimation()
                
                with Container(classes="bottom-card"):
                    yield DashboardCard(
                        "Upcoming",
                        "No upcoming tasks"
                    )

    def on_mount(self) -> None:
        if self.tasks_to_mount is not None:
            self._do_mount_tasks(self.tasks_to_mount)
            self.tasks_to_mount = None

    def mount_tasks(self, tasks):
        if self.is_mounted:
            self._do_mount_tasks(tasks)
        else:
            self.tasks_to_mount = tasks

    def _do_mount_tasks(self, tasks):
        tasks_list = self.query_one("#today-tasks-list")
        tasks_list.remove_children()
        
        if tasks:
            for task in tasks:
                tasks_list.mount(Task(task))
        else:
            tasks_list.mount(Static("No tasks scheduled for today", classes="empty-schedule"))

class WelcomeMessage(Static):
    DEFAULT_CSS = """
    WelcomeMessage {
        width: 100%;
        height: auto;
        content-align: center middle;
        text-align: center;
        padding: 1;
    }
    """

class WelcomeContent(Container):
    DEFAULT_CSS = """
    WelcomeContent {
        width: 100%;
        height: 100%;
        align: center middle;
        padding: 2;
    }
    """
    
    def compose(self):
        yield WelcomeMessage("║       Welcome to TICK        ║")
        yield WelcomeMessage("")
        yield WelcomeMessage("For detailed instructions, reference the docs on the GitHub | https://github.com/cachebag/tick ")
        yield WelcomeMessage("")
        yield WelcomeMessage("Navigation:")
        yield WelcomeMessage("• Use ↑/↓ arrows to navigate the menu")
        yield WelcomeMessage("• Press Enter to select a menu item")
        yield WelcomeMessage("• Press Ctrl+Q to quit")
        yield WelcomeMessage("• Press Esc to toggle the menu")
        yield WelcomeMessage("")
        yield WelcomeMessage("Select an option from the menu to begin (you can use your mouse too, we don't judge.)")

class WelcomeView(Container):
    def compose(self) -> ComposeResult:
        with Horizontal(classes="tab-bar"):
            yield TabButton("Welcome", "welcome")
        
        with Container(id="tab-content"):
            yield WelcomeContent()

    def on_mount(self) -> None:
        self.query_one("TabButton").toggle_active(True)
        
        today = datetime.now().strftime('%Y-%m-%d')
        tasks = self.app.db.get_tasks_for_date(today)
        
        if tasks:
            tab_bar = self.query_one(".tab-bar")
            today_tab = TabButton("Today", "today")
            tab_bar.mount(today_tab)
            
            today_content = TodayContent()
            self.query_one("#tab-content").mount(today_content)
            today_content.styles.display = "none"
            today_content.mount_tasks(tasks)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not event.button.id.startswith("tab_"):
            return

        event.stop()
            
        tab_buttons = self.query(".tab-button")
        welcome_content = self.query_one(WelcomeContent)
        
        for button in tab_buttons:
            button.toggle_active(button.id == event.button.id)
        
        if event.button.id == "tab_welcome":
            welcome_content.styles.display = "block"
            try:
                today_content = self.query_one(TodayContent)
                today_content.styles.display = "none"
            except Exception:
                pass
        elif event.button.id == "tab_today":
            welcome_content.styles.display = "none"
            try:
                today_content = self.query_one(TodayContent)
                today_content.styles.display = "block"
            except Exception:
                pass
