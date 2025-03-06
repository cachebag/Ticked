import getpass
import platform
from datetime import datetime

import psutil
from textual.widgets import Static


class SystemStatsHeader(Static):

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

        self.update(
            f"UPTIME: {uptime} | CPU% {cpu} | MEM%: {mem} | user: {self.user_name}"
        )


def get_system_info():
    try:
        os_name = platform.system()
        os_version = platform.version()

        python_version = platform.python_version()

        memory = psutil.virtual_memory()
        memory_total = memory.total / (1024 * 1024)
        memory_available = memory.available / (1024 * 1024)

        cpu_percent = psutil.cpu_percent(interval=0.1)

        return {
            "os_name": os_name,
            "os_version": os_version,
            "python_version": python_version,
            "memory_total": memory_total,
            "memory_available": memory_available,
            "cpu_percent": cpu_percent,
            "python_implementation": platform.python_implementation(),
        }
    except Exception as e:
        return {
            "error": str(e),
            "os_name": platform.system(),
            "python_version": platform.python_version(),
        }
