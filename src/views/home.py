# home.py
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Button, Static, Footer
from textual.binding import Binding
from .welcome import WelcomeView
from .calendar import CalendarView

class MenuItem(Button):
    """A custom button for menu items with specific styling."""
    def __init__(self, label: str, id: str) -> None:
        super().__init__(label, id=id)
        self.can_focus = True

class MainMenu(Container):
    """The main menu sidebar."""
    def compose(self) -> ComposeResult:
        yield Static("MENU", classes="menu-header")
        yield MenuItem("CALENDAR", id="menu_calendar")
        yield MenuItem("NOTES", id="menu_notes")
        yield MenuItem("YOUTUBE", id="menu_youtube")
        yield MenuItem("SPOTIFY", id="menu_spotify")
        yield MenuItem("SETTINGS", id="menu_settings")
        yield MenuItem("EXIT", id="menu_exit")

class HomeScreen(Screen):
    """The main home screen of the application."""
    
    BINDINGS = [
        Binding("escape", "toggle_menu", "Toggle Menu", show=True),
        Binding("q", "quit_app", "Quit Application", show=True),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        content_container = Container(
            WelcomeView(),
            id="content",
        )
        content_container.styles.expand = True
        yield Horizontal(
            MainMenu(),
            content_container
        )
    
        yield Footer()

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_toggle_menu(self) -> None:
        """Toggle the menu visibility."""
        menu = self.query_one("MainMenu")
        if "hidden" in menu.classes:
            menu.remove_class("hidden")
            menu.styles.width = "25"
            menu.styles.display = "block"
        else:
            menu.add_class("hidden")
            menu.styles.width = "0"
            menu.styles.display = "none"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the menu."""
        content_container = self.query_one("#content")
        menu = self.query_one("MainMenu")
        button_id = event.button.id
    
        # Clear existing content
        content_container.remove_children()
    
        if button_id == "menu_calendar":
            # Hide menu when entering calendar
            menu.add_class("hidden")
            calendar_view = CalendarView()
            calendar_view.styles.expand = True
            content_container.mount(calendar_view)
        elif button_id == "menu_notes":
            menu.remove_class("hidden")
            self.notify("Notes - Coming Soon")
        elif button_id == "menu_youtube":
            menu.remove_class("hidden")
            self.notify("YouTube - Coming Soon")
        elif button_id == "menu_spotify":
            menu.remove_class("hidden")
            self.notify("Spotify - Coming Soon")
        elif button_id == "menu_settings":
            menu.remove_class("hidden")
            self.notify("Settings - Coming Soon")
        elif button_id == "menu_exit":
            self.action_quit_app()
