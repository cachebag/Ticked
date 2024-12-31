from textual.app import App
from views.home import HomeScreen
from textual.binding import Binding
from textual.widgets import Button
from database.calendar_db import CalendarDB

class Tick(App):
    CSS_PATH = "theme.tcss"
    SCREENS = {"home": HomeScreen}
    TITLE = "TICK"
    # COMMANDS = set()
    # DEFAULT_SCREENS = {}
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("up", "focus_previous", "Move Up", show=True),
        Binding("down", "focus_next", "Move Down", show=True),
        Binding("left", "focus_previous", "Move Left", show=True),
        Binding("right", "focus_next", "Move Right", show=True),
        Binding("enter", "select", "Select", show=True),
        Binding("escape", "toggle_menu", "Toggle Menu", show=True),
    ]

    
    def __init__(self):
        super().__init__()
        self.db = CalendarDB()
    
    def on_mount(self) -> None:
        self.push_screen("home")
        self.theme = "gruvbox"

    def on_screen_resume(self) -> None:
        try:
            first_menu_item = self.screen.query_one("MenuItem")
            if first_menu_item:
                first_menu_item.focus()
        except Exception:
            pass

if __name__ == "__main__":
    app = Tick()
    app.run()

