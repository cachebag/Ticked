from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer 
from textual.screen import Screen
from textual.widgets import Header, Button, Static, Footer
from textual.binding import Binding
from .welcome import WelcomeView
from .calendar import CalendarView
from .system_stats import SystemStatsHeader

class MenuItem(Button):
    def __init__(self, label: str, id: str) -> None:
        super().__init__(label, id=id)
        self.can_focus = True

class MainMenu(Container):
    def compose(self) -> ComposeResult:
        yield Static("MENU", classes="menu-header")
        yield MenuItem("HOME", id="menu_home")
        yield MenuItem("CALENDAR", id="menu_calendar")
        yield MenuItem("NOTES", id="menu_notes")
        yield MenuItem("POMODORO", id="menu_pomodoro")
        yield MenuItem("YOUTUBE", id="menu_youtube")
        yield MenuItem("SPOTIFY", id="menu_spotify")
        yield MenuItem("SETTINGS", id="menu_settings")
        yield MenuItem("EXIT", id="menu_exit")

class CustomHeader(Container):
    def compose(self) -> ComposeResult:
        yield SystemStatsHeader()
        yield Header(show_clock=True)

class HomeScreen(Screen):
    
    BINDINGS = [
        Binding("escape", "toggle_menu", "Toggle Menu", show=True),
        Binding("q", "quit_app", "Quit Application", show=True),
    ]
    
    def compose(self) -> ComposeResult:
        yield CustomHeader()

        yield Container(
            MainMenu(),
            ScrollableContainer(
                WelcomeView(),
                id="content"
            ),
            id="main-container",
            classes="content-area"
        )

        yield Footer()

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_toggle_menu(self) -> None:
        menu = self.query_one("MainMenu")
        if "hidden" in menu.classes:
            menu.remove_class("hidden")
            menu.styles.display = "block"  # Ensure menu is displayed
            # This helps continuously keep focus for keyboard navigation when the sidebar is toggled
            try:
                first_menu_item = menu.query_one("MenuItem")
                if first_menu_item:
                    first_menu_item.focus()
            except Exception:
                self.notify("Could not focus menu item")
        else:
            menu.add_class("hidden")

    def on_mount(self) -> None:
        menu = self.query_one("MainMenu")
        menu.add_class("hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        content_container = self.query_one("#content")
        button_id = event.button.id
        menu = self.query_one("MainMenu")
    
        content_container.remove_children()
    
        try:
            if button_id == "menu_home":
                menu.add_class("hidden")
                home_view = WelcomeView()
                content_container.mount(home_view)  # Remove duplicate mount
            elif button_id == "menu_calendar":
                calendar_view = CalendarView()
                content_container.mount(calendar_view)
                menu.add_class("hidden")
            elif button_id == "menu_notes":
                menu.add_class("hidden")
                self.notify("Coming Soon!", severity="warning")
            elif button_id == "menu_pomodoro":
                menu.add_class("hidden")
                self.notify("Coming Soon!", severity="warning")
            elif button_id == "menu_youtube":
                menu.add_class("hidden")
                self.notify("Coming Soon!", severity="warning")
            elif button_id == "menu_spotify":
                menu.add_class("hidden")
                self.notify("Coming Soon!", severity="warning")
            elif button_id == "menu_settings":
                menu.add_class("hidden")
                self.notify("Coming Soon!", severity="warning")
            elif button_id == "menu_exit":
                self.action_quit_app()
        except Exception as e:
            self.notify(f"Error: {str(e)}")
