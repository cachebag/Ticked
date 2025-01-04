from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer 
from textual.screen import Screen
from textual.widgets import Header, Button, Static, Footer
from textual.binding import Binding
from src.ui.views.welcome import WelcomeView
from src.ui.views.calendar import CalendarView
from src.utils.system_stats import SystemStatsHeader
from src.ui.views.nest import NestView
from src.ui.views.settings import SettingsView
from src.ui.mixins.focus_mixin import InitialFocusMixin
from textual.widget import Widget
from typing import Optional
from ..views.pomodoro import PomodoroView   
from ..views.spotify import SpotifyView 
from .loading_screen import LoadingScreen
import asyncio


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

class HomeScreen(Screen, InitialFocusMixin):
    
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
        content_container = self.query_one("#content")
        
        if "hidden" in menu.classes:
            menu.remove_class("hidden")
            menu.styles.display = "block"
            first_menu_item = menu.query_one("MenuItem")
            if first_menu_item:
                first_menu_item.focus()
        else:
            menu.add_class("hidden")
            menu.styles.display = "none"
            
            if content_container and content_container.children:
                current_view = content_container.children[0]
                
                try:
                    if isinstance(current_view, WelcomeView):
                        tab = current_view.query("TabButton").first()
                        if tab:
                            tab.focus()
                            return
                    
                    if hasattr(current_view, 'get_initial_focus'):
                        initial_focus = current_view.get_initial_focus()
                        if initial_focus:
                            initial_focus.focus()
                            return
                except Exception:
                    current_view.focus()

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
        menu.styles.display = "none"
        first_menu_item = menu.query_one("MenuItem")
        if first_menu_item:
            first_menu_item.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        content_container = self.query_one("#content")
        button_id = event.button.id
        menu = self.query_one("MainMenu")

        menu.add_class("hidden")
        menu.styles.display = "none"

        try:
            if button_id == "menu_home":
                loading = LoadingScreen(animation_style=0)
                content_container.remove_children()
                content_container.mount(loading)
                
                async def load_home():
                    await loading.start_loading(0.2)
                    content_container.remove_children()
                    home_view = WelcomeView()
                    content_container.mount(home_view)
                    try:
                        tab = home_view.query("TabButton").first()
                        if tab:
                            tab.focus()
                    except Exception:
                        home_view.focus()
                        
                asyncio.create_task(load_home())
                
            elif button_id == "menu_calendar":
                loading = LoadingScreen(animation_style=1) 
                content_container.remove_children()
                content_container.mount(loading)
                
                async def load_calendar():
                    await loading.start_loading(0)
                    content_container.remove_children()
                    calendar_view = CalendarView()
                    content_container.mount(calendar_view)
                    try:
                        if hasattr(calendar_view, 'get_initial_focus'):
                            initial_focus = calendar_view.get_initial_focus()
                            if initial_focus:
                                initial_focus.focus()
                    except Exception:
                        calendar_view.focus()
                        
                asyncio.create_task(load_calendar())
                
            elif button_id == "menu_nest":
                loading = LoadingScreen(animation_style=2) 
                content_container.remove_children()
                content_container.mount(loading)
                
                async def load_nest():
                    await loading.start_loading(0)
                    content_container.remove_children()
                    nest_view = NestView()
                    content_container.mount(nest_view)
                    
                asyncio.create_task(load_nest())
                
            elif button_id == "menu_pomodoro":
                loading = LoadingScreen(animation_style=3)  
                content_container.remove_children()
                content_container.mount(loading)
                
                async def load_pomodoro():
                    await loading.start_loading(0)
                    content_container.remove_children()
                    pomo_view = PomodoroView()
                    content_container.mount(pomo_view)
                    
                asyncio.create_task(load_pomodoro())
                
            elif button_id == "menu_spotify":
                loading = LoadingScreen(animation_style=0)  
                content_container.remove_children()
                content_container.mount(loading)
                
                async def load_spotify():
                    await loading.start_loading(2.0)
                    content_container.remove_children()
                    spotify_view = SpotifyView()
                    content_container.mount(spotify_view)
                    
                asyncio.create_task(load_spotify())
                
            elif button_id == "menu_settings":
                loading = LoadingScreen(animation_style=1) 
                content_container.remove_children()
                content_container.mount(loading)
                
                async def load_settings():
                    await loading.start_loading(0)
                    content_container.remove_children()
                    settings_view = SettingsView()
                    content_container.mount(settings_view)
                    
                asyncio.create_task(load_settings())
                
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

    def get_initial_focus(self) -> Optional[Widget]:
        return self.query_one("MenuItem")


    async def _switch_view(self, view_class, *args, **kwargs):
        content_container = self.query_one("#content")
        content_container.remove_children()
        
        loading = LoadingScreen(animation_style=0)  
        content_container.mount(loading)
        
        new_view = view_class(*args, **kwargs)
        
        loading_task = asyncio.create_task(loading.start_loading(0.3)) 
        
        try:
            await loading_task
            
            content_container.remove_children()
            content_container.mount(new_view)
            
            try:
                if isinstance(new_view, WelcomeView):
                    tab = new_view.query("TabButton").first()
                    if tab:
                        tab.focus()
                elif hasattr(new_view, 'get_initial_focus'):
                    initial_focus = new_view.get_initial_focus()
                    if initial_focus:
                        initial_focus.focus()
                else:
                    new_view.focus()
            except Exception:
                new_view.focus()
                
        except Exception as e:
            self.notify(f"Error: {str(e)}")