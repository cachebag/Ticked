import asyncio
import json
from pathlib import Path

import pyfiglet
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class CustomizeModal(ModalScreen[dict]):

    def __init__(self, name=None, id=None, classes=None):
        super().__init__(name=name, id=id, classes=classes)
        self.package_dir = Path(__file__).parent.parent.parent

    def compose(self) -> ComposeResult:
        with Container(classes="customize-dialog"):
            yield Label("Session time (minutes):")
            yield Input(
                value=str(self.app.get_current_settings()["work_duration"]),
                id="work_duration",
            )
            yield Label("Break time (minutes):")
            yield Input(
                value=str(self.app.get_current_settings()["break_duration"]),
                id="break_duration",
            )
            yield Label("Number of sessions (max 12):")
            yield Input(
                value=str(self.app.get_current_settings()["total_sessions"]),
                id="total_sessions",
            )
            yield Label("Long break time (minutes):")
            yield Input(
                value=str(self.app.get_current_settings()["long_break_duration"]),
                id="long_break_duration",
            )
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "save":
            try:
                settings = {
                    "work_duration": int(self.query_one("#work_duration").value),
                    "break_duration": int(self.query_one("#break_duration").value),
                    "total_sessions": min(
                        12, int(self.query_one("#total_sessions").value)
                    ),
                    "long_break_duration": int(
                        self.query_one("#long_break_duration").value
                    ),
                }
                pomo = self.package_dir / "pomodoro_settings.json"
                with open(pomo, "w") as f:
                    json.dump(settings, f)
                self.app.update_settings(settings)
                self.dismiss(settings)
            except ValueError:
                self.app.notify("Please enter valid numbers")
        else:
            self.dismiss(None)


class PomodoroView(Container):
    work_duration = reactive(25)
    break_duration = reactive(5)
    total_sessions = reactive(4)
    long_break_duration = reactive(15)
    is_break = reactive(False)
    time_left = reactive(25 * 60)
    current_session = reactive(1)

    BINDINGS = [
        Binding("space", "toggle", "Start/Pause"),
        Binding("r", "reset", "Reset"),
    ]

    def __init__(self):
        super().__init__()
        self._is_running = False
        self.timer_task = None
        self.timer_display = Static("", id="timer_display")
        self.session_counter = Static("", id="session_counter")

    def compose(self) -> ComposeResult:
        with Container(classes="pomodoro-container"):
            yield self.timer_display
            yield self.session_counter
            with Vertical(classes="timer-controls"):
                yield Button("Start/Pause", id="toggle", classes="control-button")
                yield Button("Reset", id="reset", classes="control-button")
                yield Button("Customize", id="customize", classes="control-button")

    async def timer_countdown(self):
        while self.time_left > 0 and self._is_running:
            await asyncio.sleep(1)
            self.time_left -= 1

            if self.time_left == 0:
                self.is_break = not self.is_break
                if self.is_break:
                    if self.current_session < self.total_sessions:
                        self.time_left = self.break_duration * 60
                    else:
                        self.time_left = self.long_break_duration * 60
                        self.current_session = 1
                else:
                    self.current_session += 1
                    self.time_left = self.work_duration * 60

    def watch_work_duration(self, new_value: int) -> None:
        if not self.is_break:
            self.time_left = new_value * 60
            self.update_display()

    def watch_break_duration(self, new_value: int) -> None:
        if self.is_break and self.current_session < self.total_sessions:
            self.time_left = new_value * 60
            self.update_display()

    def watch_long_break_duration(self, new_value: int) -> None:
        if self.is_break and self.current_session >= self.total_sessions:
            self.time_left = new_value * 60
            self.update_display()

    def watch_current_session(self, new_value: int) -> None:
        self.update_session_counter()

    def watch_time_left(self, new_value: int) -> None:
        self.update_display()

    def update_session_counter(self):
        self.session_counter.update(
            f"Session {self.current_session}/{self.total_sessions}"
        )

    def update_display(self):
        minutes = f"{self.time_left // 60:02d}".replace("", " ")[1:-1]
        seconds = f"{self.time_left % 60:02d}".replace("", " ")[1:-1]
        time_string = f"{minutes}  :  {seconds}"
        ascii_art = pyfiglet.figlet_format(time_string, font="colossal")
        self.timer_display.update(ascii_art)
        self.timer_display.refresh(layout=True)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "toggle":
            self.action_toggle()
        elif event.button.id == "reset":
            self.action_reset()
        elif event.button.id == "customize":
            self.action_customize()

    @work
    async def action_customize(self):
        modal = CustomizeModal()
        settings = await self.app.push_screen_wait(modal)
        if settings:
            self._is_running = False
            if self.timer_task and not self.timer_task.done():
                self.timer_task.cancel()
            self.work_duration = settings["work_duration"]
            self.break_duration = settings["break_duration"]
            self.total_sessions = settings["total_sessions"]
            self.long_break_duration = settings["long_break_duration"]
            self.is_break = False
            self.time_left = self.work_duration * 60
            self.current_session = 1
            self.query_one("#toggle").label = "Start"
            self.update_display()
            self.update_session_counter()

    def action_toggle(self):
        self._is_running = not self._is_running
        toggle_button = self.query_one("#toggle")

        if self._is_running:
            toggle_button.label = "Pause"
            if not self.timer_task or self.timer_task.done():
                self.timer_task = asyncio.create_task(self.timer_countdown())
        else:
            toggle_button.label = "Start"

    def action_reset(self):
        self._is_running = False
        self.is_break = False
        self.time_left = self.work_duration * 60
        self.current_session = 1
        toggle_button = self.query_one("#toggle")
        toggle_button.label = "Start"
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()

    def on_mount(self):
        settings = self.app.get_current_settings()
        self.work_duration = settings["work_duration"]
        self.break_duration = settings["break_duration"]
        self.total_sessions = settings["total_sessions"]
        self.long_break_duration = settings["long_break_duration"]
        self.time_left = self.work_duration * 60
        self.update_display()
        self.update_session_counter()
