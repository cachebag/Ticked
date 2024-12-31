from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer 
from textual.screen import Screen
from textual.widgets import Header, Button, Static, Footer
from textual.binding import Binding
from .welcome import WelcomeView
from .calendar import CalendarView
from .system_stats import SystemStatsHeader
from .nest import NestView

class MenuItem(Button):
    def __init__(self, label: str, id: str) -> None:
        super().__init__(label, id=id)
        self.can_focus = True

class MainMenu(Container):
    def compose(self) -> ComposeResult:
        yield Static("MENU", classes="menu-header")
        yield MenuItem("HOME", id="menu_home")
        yield MenuItem("CALENDAR", id="menu_calendar")
        yield MenuItem("NEST+", id="menu_nest")
        yield MenuItem("POMODORO", id="menu_pomodoro")
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
        Binding("up", "menu_up", "Up", show=True),
        Binding("down", "menu_down", "Down", show=True),
        Binding("enter", "menu_select", "", show=False),
        Binding("left", "move_left", "", show=False),
        Binding("right", "move_right", "", show=False)
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

    def is_menu_visible(self) -> bool:
        menu = self.query_one("MainMenu")
        return "hidden" not in menu.classes

    def action_toggle_menu(self) -> None:
        menu = self.query_one("MainMenu")
        if "hidden" in menu.classes:
            menu.remove_class("hidden")
            menu.styles.display = "block"
            try:
                first_menu_item = menu.query_one("MenuItem")
                if first_menu_item:
                    first_menu_item.focus()
            except Exception:
                self.notify("Could not focus menu item")
        else:
            menu.add_class("hidden")
            content = self.query_one("#content")
            if content and content.children:
                current_view = content.children[0]
            
                if isinstance(current_view, WelcomeView):
                    try:
                        today_tab = current_view.query_one("TabButton#tab_today")
                        if today_tab:
                            today_tab.focus()
                        return
                    except Exception:
                        pass
            
                elif isinstance(current_view, CalendarView):
                    try:
                        day_view = current_view.query_one(DayView)
                        if day_view and day_view.styles.display == "block":
                            add_task = day_view.query_one("#add-task")
                            if add_task:
                                add_task.focus()
                                return
                    except Exception:
                        pass
                
                    try:
                        current_day = current_view.query_one(".current-day")
                        if current_day:
                            current_day.focus()
                            return
                        else:
                            first_day = current_view.query_one("CalendarDayButton")
                            if first_day:
                                first_day.focus()
                                return
                    except Exception:
                        pass
            
                elif isinstance(current_view, NestView):
                    try:
                        tree = current_view.query_one("FilterableDirectoryTree")
                        if tree:
                            tree.focus()
                        return
                    except Exception:
                        pass
            
                content.focus() 

    def action_menu_up(self) -> None:
        if self.is_menu_visible():
            menu = self.query_one("MainMenu")
            menu_items = list(menu.query("MenuItem"))
            current = self.focused
            
            if current in menu_items:
                current_idx = menu_items.index(current)
                prev_idx = (current_idx - 1) % len(menu_items)
                menu_items[prev_idx].focus()

    def action_menu_down(self) -> None:
        if self.is_menu_visible():
            menu = self.query_one("MainMenu")
            menu_items = list(menu.query("MenuItem"))
            current = self.focused
            
            if current in menu_items:
                current_idx = menu_items.index(current)
                next_idx = (current_idx + 1) % len(menu_items)
                menu_items[next_idx].focus()

    def action_menu_select(self) -> None:
        if self.is_menu_visible() and isinstance(self.focused, MenuItem):
            self.focused.press()

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
                content_container.mount(home_view)  
            elif button_id == "menu_calendar":
                menu.add_class("hidden")
                calendar_view = CalendarView()
                content_container.mount(calendar_view)
            elif button_id == "menu_nest":
                menu.add_class("hidden")
                nest_view = NestView()
                content_container.mount(nest_view)
            elif button_id == "menu_pomodoro":
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

    def on_focus(self, event) -> None:
        if self.is_menu_visible():
            menu = self.query_one("MainMenu")
            if not isinstance(event.control, (MenuItem, MainMenu)):
                event.prevent_default()
                event.stop()
                current_menu_item = menu.query("MenuItem").first()
                for item in menu.query("MenuItem"):
                    if item.has_focus:
                        current_menu_item = item
                        break
                current_menu_item.focus()

    def on_key(self, event) -> None:
        if self.is_menu_visible():
            allowed_keys = {"escape", "up", "down", "enter"}
            if event.key not in allowed_keys:
                event.prevent_default()
                event.stop()

    def action_focus_previous(self) -> None:
        if not self.is_menu_visible():
            return
        self.action_menu_up()

    def action_focus_next(self) -> None:
        if not self.is_menu_visible():
            return
        self.action_menu_down()
