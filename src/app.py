from textual.app import App
from src.ui.screens.home import HomeScreen
from textual.binding import Binding
from src.core.database.calendar_db import CalendarDB
import os


class Tick(App):
    CSS_PATH = "config/theme.tcss"
    SCREENS = {"home": HomeScreen}
    TITLE = "TICK"
    
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
            if (first_menu_item):
                first_menu_item.focus()
        except Exception:
            pass

    async def action_new_file(self) -> None:
        """Create a new file."""
        current_path = os.getcwd()
        dialog = NewFileDialog(current_path)
        result = await self.push_screen(dialog)
        
        if result:
            self.notify(f"Created new file: {os.path.basename(result)}")

    def action_toggle_menu(self) -> None:
        """Toggle the main menu visibility."""
        try:
            menu = self.query_one("MainMenu")
            is_hidden = "hidden" in menu.classes
            
            if is_hidden:
                menu.remove_class("hidden")
                for item in menu.query("MenuItem"):
                    item.can_focus = True
            else:
                menu.add_class("hidden")
                for item in menu.query("MenuItem"):
                    item.can_focus = False
                
                current_view = self.screen.query_one(".content").children[0]
                if hasattr(current_view, 'get_initial_focus'):
                    initial_focus = current_view.get_initial_focus()
                    if (initial_focus):
                        initial_focus.focus()
                        
        except Exception as e:
            self.notify(f"Error toggling menu: {str(e)}", severity="error")

if __name__ == "__main__":
    app = Tick()
    app.run()

