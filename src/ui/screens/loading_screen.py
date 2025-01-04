from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual.message import Message
import asyncio

class LoadingScreen(Container):
    
    class LoadingComplete(Message):
        pass
    
    ANIMATIONS = [
        "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",  
        "▁▂▃▄▅▆▇█▇▆▅▄▃▂▁",  
        "⣾⣽⣻⢿⡿⣟⣯⣷",     
        "←↖↑↗→↘↓↙"          
    ]
    
    def __init__(self, animation_style: int = 0) -> None:
        super().__init__()
        self.animation = self.ANIMATIONS[animation_style]
        self.frame = 0
        self.running = True
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Loading...", id="loading-text", classes="loading-text"),
            Static("", id="loading-animation", classes="loading-animation"),
            classes="loading-container"
        )
    
    async def animate(self) -> None:
        animation_widget = self.query_one("#loading-animation")
        while self.running:
            self.frame = (self.frame + 1) % len(self.animation)
            animation_widget.update(self.animation[self.frame])
            await asyncio.sleep(0.1)
    
    def on_mount(self) -> None:
        self.styles.align_horizontal = "center"
        self.styles.align_vertical = "middle"
        self.styles.width = "100%"
        self.styles.height = "100%"
        asyncio.create_task(self.animate())
    
    async def start_loading(self, duration: float = 2.0) -> None:
        await asyncio.sleep(duration)
        self.running = False
        self.post_message(self.LoadingComplete())
