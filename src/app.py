from textual.app import App, ComposeResult
from src.ui.screens.home import HomeScreen
from textual.binding import Binding
from textual.widgets import Button
from src.core.database.calendar_db import CalendarDB
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Input, DirectoryTree, Label, Static
from textual.message import Message
import os

class NewFileDialog(ModalScreen):
    def __init__(self, initial_path: str) -> None:
        super().__init__()
        self.selected_path = initial_path

    def compose(self) -> ComposeResult:
        with Container(classes="task-form-container"):
            with Vertical(classes="task-form"):
                yield Static("Create New File", classes="form-header")
                
                with Vertical():
                    yield Label("Selected Directory:")
                    yield Static(str(self.selected_path), id="selected-path")

                with Vertical():
                    yield Label("Filename")
                    yield Input(placeholder="Enter filename", id="filename")

                yield DirectoryTree(os.path.expanduser("~"))

                with Horizontal(classes="form-buttons"):
                    yield Button("Cancel", variant="error", id="cancel")
                    yield Button("Create File", variant="success", id="submit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            filename = self.query_one("#filename").value
            tree = self.query_one(DirectoryTree)
            selected_path = tree.selected_path or self.selected_path
            
            if filename and selected_path:
                full_path = os.path.join(selected_path, filename)
                try:
                    with open(full_path, 'w') as f:
                        f.write("")
                    self.dismiss(full_path)
                except Exception as e:
                    self.notify(f"Error creating file: {str(e)}", severity="error")
        else:
            self.dismiss(None)

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
        Binding("ctrl+n", "new_file", "New File", show=True),  # Add this line
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

    async def action_new_file(self) -> None:
        """Create a new file."""
        current_path = os.getcwd()
        dialog = NewFileDialog(current_path)
        result = await self.push_screen(dialog)
        
        if result:
            self.notify(f"Created new file: {os.path.basename(result)}")
            # You might want to dispatch an event here to notify the editor
            self.post_message(self.NewFileCreated(result))

    def action_toggle_menu(self) -> None:
        """Toggle the main menu visibility."""
        try:
            menu = self.query_one("MainMenu")
            is_hidden = "hidden" in menu.classes
            
            if is_hidden:
                menu.remove_class("hidden")
                # Only allow focusing menu items when menu is visible
                for item in menu.query("MenuItem"):
                    item.can_focus = True
            else:
                menu.add_class("hidden")
                # Prevent focusing menu items when menu is hidden
                for item in menu.query("MenuItem"):
                    item.can_focus = False
                
                # Move focus to the current view's initial focus if needed
                current_view = self.screen.query_one(".content").children[0]
                if hasattr(current_view, 'get_initial_focus'):
                    initial_focus = current_view.get_initial_focus()
                    if initial_focus:
                        initial_focus.focus()
                        
        except Exception as e:
            self.notify(f"Error toggling menu: {str(e)}", severity="error")

    class NewFileCreated(Message):
        """Posted when a new file is created."""
        def __init__(self, path: str):
            super().__init__()
            self.path = path

if __name__ == "__main__":
    app = Tick()
    app.run()

