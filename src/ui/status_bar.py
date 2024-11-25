# src/ui/status_bar.py
import time
from ..utils.constants import ACTIVE_DOT, CURSOR
from ..utils.system_monitor import SystemMonitor

class StatusBar:
    def __init__(self):
        self.start_time = time.time()
        self.system_monitor = SystemMonitor()
        self.cursor_visible = True
        self.last_blink = time.time()

    def get_uptime(self) -> str:
        elapsed = int(time.time() - self.start_time)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def should_blink_cursor(self) -> bool:
        current_time = time.time()
        if current_time - self.last_blink >= 0.5:
            self.cursor_visible = not self.cursor_visible
            self.last_blink = current_time
        return self.cursor_visible