from textual.app import App, ComposeResult
from textual.screen import Screen
from .ui.views.nest import NewFileDialog
from .ui.views.pomodoro import PomodoroView
from .ui.screens.home import HomeScreen
from .ui.views.nest import NestView
from textual.dom import NoMatches
from textual.binding import Binding
from textual import events
from .core.database.ticked_db import CalendarDB
import os
import json

class Ticked(App):
    CSS_PATH = "config/theme.tcss"
    SCREENS = {"home": HomeScreen}
    TITLE = "TICKED"
    COMMANDS = {}
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
        self.pomodoro_settings = self.load_settings()

    def get_spotify_client(self):
        if hasattr(self, '_spotify_auth') and self._spotify_auth:
            return self._spotify_auth.spotify_client
        return None
        
    def set_spotify_auth(self, auth):
        self._spotify_auth = auth

    def load_settings(self):
        default_settings = {
            "work_duration": 25,
            "break_duration": 5,
            "total_sessions": 4,
            "long_break_duration": 15
        }
        try:
            with open("pomodoro_settings.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            with open("pomodoro_settings.json", "w") as f:
                json.dump(default_settings, f)
            return default_settings

    def get_current_settings(self):
        return self.pomodoro_settings

    def update_settings(self, new_settings):
        self.pomodoro_settings = new_settings
        if isinstance(self.screen, Screen):
            for view in self.screen.walk_children(PomodoroView):
                view.work_duration = new_settings["work_duration"]
                view.break_duration = new_settings["break_duration"]
                view.total_sessions = new_settings["total_sessions"]
                view.long_break_duration = new_settings["long_break_duration"]

    async def on_shutdown(self) -> None:
        await self.db.close()
        await super().on_shutdown()

    def on_mount(self) -> None:
        self.push_screen("home")
        self.theme = "gruvbox"

    async def on_mouse_move(self, event: events.MouseMove) -> None:
        try:
            hover_target = self.query_one(".hoverable")
            hover_target.focus()
        except NoMatches:
            pass

    async def on_mouse_down(self, event: events.MouseDown) -> None:
        pass

    async def action_new_file(self) -> None:
        current_path = os.getcwd()
        dialog = NewFileDialog(current_path)
        result = await self.push_screen(dialog)
        if result:
            self.notify(f"Created new file: {os.path.basename(result)}")

    def action_toggle_menu(self) -> None:
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
                    if initial_focus:
                        initial_focus.focus()
        except Exception as e:
            self.notify(f"Error toggling menu: {str(e)}", severity="error")

    def compose(self) -> ComposeResult:
        yield NestView()

if __name__ == "__main__":
    app = Ticked()
    app.run()
