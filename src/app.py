from textual.app import App
from views.home import HomeScreen
from textual.binding import Binding
from textual.widgets import Footer
from database.calendar_db import CalendarDB
import os
from views.nest import FilterableDirectoryTree, NewFileDialog, CodeEditor, NestView  

class Tick(App):
    """Main application class."""
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
        Binding("ctrl+n", "new_file", "New File", priority=True),
    ]

    
    def __init__(self):
        super().__init__()
        self.devtools = None
        self._batch_count = 0
        self.db = CalendarDB()
    
    def compose(self):
        yield NestView()
        yield Footer()

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

    async def action_new_file(self) -> None:
        try:
            nest_view = self.screen.query_one("NestView")
            if not nest_view:
                content = self.screen.query_one("#content")
                if content:
                    content.remove_children()
                    from views.nest import NestView
                    nest_view = NestView()
                    content.mount(nest_view)
                    menu = self.screen.query_one("MainMenu")
                    if menu and "hidden" not in menu.classes:
                        menu.add_class("hidden")

            tree = nest_view.query_one(FilterableDirectoryTree)
            current_path = tree.path if tree.path else os.path.expanduser("~")
            
            dialog = NewFileDialog(current_path)
            result = await self.push_screen(dialog)
            
            if result:
                tree = nest_view.query_one(FilterableDirectoryTree)
                editor = nest_view.query_one(CodeEditor)
                
                tree.reload()
                editor.load_text("")
                editor.current_file = result
                editor.set_language_from_file(result)
                editor.mode = "normal"
                editor.focus()
                
                self.notify(f"Created new file: {os.path.basename(result)}")
        except Exception as e:
            self.notify(f"Error creating file: {str(e)}", severity="error")

if __name__ == "__main__":
    app = Tick()
    app.run()

