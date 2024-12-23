# views/home.py
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Button, Static, Footer
from textual.binding import Binding
from views.welcome import WelcomeView

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
        Binding("escape", "quit_app", "Quit Application", show=True),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            MainMenu(),
            Container(
                WelcomeView(),
                id="content"
            )
        )
        yield Footer()

    def action_quit_app(self) -> None:
        self.app.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the menu."""
        button_id = event.button.id
        if button_id == "menu_calendar":
            self.notify("Calendar - Coming Soon")
        elif button_id == "menu_notes":
            self.notify("Notes - Coming Soon")
        elif button_id == "menu_youtube":
            self.notify("YouTube - Coming Soon")
        elif button_id == "menu_spotify":
            self.notify("Spotify - Coming Soon")
        elif button_id == "menu_settings":
            self.notify("Settings - Coming Soon")
        elif button_id == "menu_exit":
            self.action_quit_app()
