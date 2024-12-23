# views/welcome.py
from textual.widgets import Static
from textual.containers import Container

class WelcomeMessage(Static):
    """A styled welcome message widget."""
    DEFAULT_CSS = """
    WelcomeMessage {
        width: 100%;
        height: auto;
        content-align: center middle;
        text-align: center;
        padding: 1;
        color: $accent;
    }
    """

class WelcomeView(Container):
    """Welcome screen content with instructions."""
    DEFAULT_CSS = """
    WelcomeView {
        width: 100%;
        height: 100%;
        align: center middle;
        background: $surface;
        padding: 2;
    }
    """
    
    def compose(self):
        yield WelcomeMessage("║       Welcome to TICK        ║")
        yield WelcomeMessage("")
        yield WelcomeMessage("For detailed instructions, reference the docs on the GitHub: ")
        yield WelcomeMessage("")
        yield WelcomeMessage("Navigation:")
        yield WelcomeMessage("• Use ↑/↓ arrows to navigate the menu")
        yield WelcomeMessage("• Press Enter to select a menu item")
        yield WelcomeMessage("• Press Ctrl+Q or ESC to quit")
        yield WelcomeMessage("")
        yield WelcomeMessage("Select an option from the menu to begin (you can use your mouse too, we don't judge.)")
