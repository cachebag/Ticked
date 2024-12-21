import time
import psutil
import socket
import os
from typing import Dict

class SystemMonitor:
    def __init__(self):
        self.hostname = socket.gethostname()
        self.username = os.getlogin()

    def get_memory_usage(self) -> str:
        mem = psutil.virtual_memory()
        return f"{mem.used // 1024 // 1024}MB/{mem.total // 1024 // 1024}MB"

    def get_cpu_temp(self) -> str:
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        return f"{entries[0].current:.1f}°C"
        except:
            pass
        return "N/A"

    def get_load_average(self) -> str:
        try:
            load1, load5, load15 = psutil.getloadavg()
            return f"{load1:.1f}"
        except:
            return "N/A"

    def get_system_info(self) -> Dict[str, str]:
        return {
            "user": f"{self.username}@{self.hostname}",
            "mem": self.get_memory_usage(),
            "cpu_temp": self.get_cpu_temp(),
            "load": self.get_load_average()
        }
