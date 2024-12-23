# home.py
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Button, Static, Footer
from textual.binding import Binding
from .welcome import WelcomeView
from .calendar import CalendarView
from .system_stats import SystemStatsHeader

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

class CustomHeader(Container):
    """Custom header with system stats and clock."""
    def compose(self) -> ComposeResult:
        yield SystemStatsHeader()
        yield Header(show_clock=True)

class HomeScreen(Screen):
    """The main home screen of the application."""
    
    BINDINGS = [
        Binding("escape", "toggle_menu", "Toggle Menu", show=True),
        Binding("q", "quit_app", "Quit Application", show=True),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the initial layout."""
        yield CustomHeader()
        
        # Create the main container for menu and content
        yield Horizontal(
            MainMenu(),
            Container(
                WelcomeView(),
                id="content"
            )
        )
        
        yield Footer()

    def action_quit_app(self) -> None:
        """Quit the application."""
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

    def on_mount(self) -> None:
        """Handle screen mount."""
        menu = self.query_one("MainMenu")
        menu.add_class("hidden")
        menu.styles.width = "0"
        menu.styles.display = "none"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the menu."""
        content_container = self.query_one("#content")
        button_id = event.button.id
        
        # Remove existing content
        content_container.remove_children()
        
        try:
            if button_id == "menu_calendar":
                # Create and mount new calendar view
                calendar_view = CalendarView()
                content_container.mount(calendar_view)
                # Hide menu after selection
                menu = self.query_one("MainMenu")
                menu.add_class("hidden")
                menu.styles.width = "0"
                menu.styles.display = "none"
            elif button_id == "menu_notes":
                content_container.mount(Static("Notes - Coming Soon"))
            elif button_id == "menu_youtube":
                content_container.mount(Static("YouTube - Coming Soon"))
            elif button_id == "menu_spotify":
                content_container.mount(Static("Spotify - Coming Soon"))
            elif button_id == "menu_settings":
                content_container.mount(Static("Settings - Coming Soon"))
            elif button_id == "menu_exit":
                self.action_quit_app()
        except Exception as e:
            self.notify(f"Error: {str(e)}")
