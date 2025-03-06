# calendar_setup.py
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from ...core.database.caldav_sync import CalDAVSync


class CalendarSetupScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("f1", "submit", "Submit"),
    ]

    DEFAULT_OPTION = "Select Calendar"

    def compose(self) -> ComposeResult:
        config = self.app.db.get_caldav_config()
        default_options = [(self.DEFAULT_OPTION, self.DEFAULT_OPTION)]

        with Container(classes="calendar-setup-container"):
            with Vertical(classes="calendar-setup-form"):
                yield Static("CalDAV Setup", classes="form-header")

                with Vertical():
                    yield Label("Server URL")
                    yield Input(
                        value=config["url"] if config else "",
                        placeholder="https://caldav.example.com",
                        id="server-url",
                    )

                with Vertical():
                    yield Label("Username")
                    yield Input(
                        value=config["username"] if config else "", id="username"
                    )

                with Vertical():
                    yield Label("Password")
                    yield Input(
                        value=config["password"] if config else "",
                        password=True,
                        id="password",
                    )

                with Vertical():
                    yield Label("Calendar")
                    if config:
                        sync = CalDAVSync(self.app.db)
                        if sync.connect(
                            config["url"], config["username"], config["password"]
                        ):
                            calendars = sync.get_calendars()
                            if calendars:
                                calendar_options = [(cal, cal) for cal in calendars]
                                yield Select(
                                    options=calendar_options,
                                    value=config["selected_calendar"],
                                    id="calendar-select",
                                )
                            else:
                                yield Select(
                                    options=default_options,
                                    id="calendar-select",
                                    disabled=True,
                                )
                        else:
                            yield Select(
                                options=default_options,
                                id="calendar-select",
                                disabled=True,
                            )
                    else:
                        yield Select(
                            options=default_options, id="calendar-select", disabled=True
                        )

                with Horizontal(classes="form-buttons"):
                    yield Button("Test", variant="primary", id="test-connection")
                    yield Button("Cancel", variant="error", id="cancel")
                    save_button = Button("Save", variant="success", id="save")
                    save_button.disabled = not config
                    yield save_button

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "test-connection":
            self._test_connection()
        elif event.button.id == "save":
            self._save_config()

    def _test_connection(self) -> None:
        url = self.query_one("#server-url").value
        username = self.query_one("#username").value
        password = self.query_one("#password").value

        if not all([url, username, password]):
            self.notify("Please fill all fields", severity="error")
            return

        sync = CalDAVSync(self.app.db)
        if sync.connect(url, username, password):
            calendars = sync.get_calendars()

            if not calendars:
                self.notify("No calendars found!", severity="error")
                return

            select = self.query_one("#calendar-select", Select)
            select.clear()

            calendar_options = [(str(cal), str(cal)) for cal in calendars]
            select.set_options(calendar_options)

            if calendar_options:
                try:
                    first_value = str(calendar_options[0][0])
                    select.value = first_value
                    select.disabled = False
                    self.query_one("#save").disabled = False
                    self.notify(
                        f"Found {len(calendars)} calendars!", severity="information"
                    )
                except Exception as e:
                    raise
        else:
            self.notify("Connection failed", severity="error")

    def _save_config(self) -> None:
        url = self.query_one("#server-url").value
        username = self.query_one("#username").value
        password = self.query_one("#password").value
        select = self.query_one("#calendar-select")
        calendar = select.value

        if not calendar:
            self.notify("Please select a calendar", severity="error")
            return

        if self.app.db.save_caldav_config(url, username, password, calendar):
            sync = CalDAVSync(self.app.db)
            if sync.connect(url, username, password):
                sync.sync_calendar(calendar)
                self.notify("Calendar synced successfully!", severity="information")
                self.app.pop_screen()
            else:
                self.notify("Failed to sync calendar", severity="error")

    def on_select_changed(self, event: Select.Changed) -> None:
        save_button = self.query_one("#save")
        save_button.disabled = event.value == self.DEFAULT_OPTION
