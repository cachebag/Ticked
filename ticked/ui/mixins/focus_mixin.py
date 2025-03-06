from typing import Optional

from textual.widget import Widget


class InitialFocusMixin:
    """Mixin to handle initial focus for views."""

    def get_initial_focus(self) -> Optional[Widget]:
        """Override this method to return the widget that should receive initial focus."""
        return None

    def on_mount(self) -> None:
        """Handle initial focus when the view is mounted."""
        if hasattr(super(), "on_mount"):
            super().on_mount()

        initial_focus = self.get_initial_focus()
        if initial_focus:
            initial_focus.focus()
