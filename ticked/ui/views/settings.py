from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Static


class SettingsButton(Button):
    def __init__(self, label: str, setting_id: str):
        super().__init__(label, id=f"setting_{setting_id}")
        self.setting_id = setting_id
        self.add_class("setting-button")

    def toggle_active(self, is_active: bool):
        if is_active:
            self.add_class("active")
        else:
            self.remove_class("active")


class ThemeButton(Button):
    def __init__(self, theme: str):
        super().__init__(theme, id=f"theme_{theme}")
        self.theme_name = theme

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.app.theme = self.theme_name
        self.app.db.save_theme_preference(self.theme_name)


class PersonalizationContent(Container):
    def compose(self) -> ComposeResult:
        yield Static("Personalization Settings", classes="settings-title")
        with Container(classes="theme-buttons-grid"):
            themes = [
                "textual-dark",
                "textual-light",
                "nord",
                "gruvbox",
                "catppuccin-mocha",
                "dracula",
                "tokyo-night",
                "monokai",
                "flexoki",
                "catppuccin-latte",
                "solarized-light",
            ]
            for theme in themes:
                yield ThemeButton(theme)


class SettingsView(Container):
    BINDINGS = [
        Binding("up", "move_up", "Up", show=True),
        Binding("down", "move_down", "Down", show=True),
        Binding("enter", "select_setting", "Select", show=True),
    ]

    def compose(self) -> ComposeResult:
        with Container(classes="settings-container"):
            with Horizontal(classes="settings-layout"):
                with Vertical(classes="settings-sidebar"):
                    yield SettingsButton("Personalization", "personalization")

                with Container(classes="settings-content"):
                    yield PersonalizationContent()

    def on_mount(self) -> None:
        personalization_btn = self.query_one("SettingsButton#setting_personalization")
        personalization_btn.toggle_active(True)
        personalization_btn.focus()

    def get_initial_focus(self) -> Optional[Widget]:
        return self.query_one(SettingsButton, id="setting_personalization")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not isinstance(event.button, SettingsButton):
            return

        event.stop()

        setting_buttons = self.query(SettingsButton)

        personalization_content = self.query_one(PersonalizationContent)

        for button in setting_buttons:
            event.stop()
            button.toggle_active(button.id == event.button.id)

        all_content = [
            personalization_content,
        ]
        for content in all_content:
            content.styles.display = "none"

        if event.button.id == "setting_personalization":
            personalization_content.styles.display = "block"

    async def action_move_up(self) -> None:
        buttons = list(self.query(SettingsButton))
        current = self.app.focused
        if current in buttons:
            current_idx = buttons.index(current)
            prev_idx = (current_idx - 1) % len(buttons)
            buttons[prev_idx].focus()

    async def action_move_down(self) -> None:
        buttons = list(self.query(SettingsButton))
        current = self.app.focused
        if current in buttons:
            current_idx = buttons.index(current)
            next_idx = (current_idx + 1) % len(buttons)
            buttons[next_idx].focus()

    async def action_select_setting(self) -> None:
        current = self.app.focused
        if isinstance(current, SettingsButton):
            current.press()
