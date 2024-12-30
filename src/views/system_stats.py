from textual.widgets import Static
import psutil
from datetime import datetime
import getpass

class SystemStatsHeader(Static):
    """A widget that displays system statistics."""
    
    def __init__(self):
        super().__init__("")
        self.start_time = datetime.now()
        self.user_name = getpass.getuser()
    
    def on_mount(self):
        self.update_stats()
        self.set_interval(1.0, self.update_stats)
    
    def update_stats(self) -> None:
        uptime_delta = datetime.now() - self.start_time
        hours = int(uptime_delta.total_seconds() // 3600)
        minutes = int((uptime_delta.total_seconds() % 3600) // 60)
        seconds = int(uptime_delta.total_seconds() % 60)
        uptime = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        cpu = f"{psutil.cpu_percent()}%"
        memory = psutil.virtual_memory()
        mem = f"{memory.percent}%"
        
        self.update(f"UPTIME: {uptime} | CPU% {cpu} | MEM%: {mem} | user: {self.user_name}")
