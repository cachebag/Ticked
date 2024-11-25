# src/utils/system_monitor.py
import time
import psutil
import socket
import os
from typing import Dict, Tuple

class SystemMonitor:
    def __init__(self):
        self.last_net_io = self._get_net_io()
        self.last_net_time = time.time()
        self.hostname = socket.gethostname()
        self.username = os.getlogin()

    def _get_net_io(self) -> Tuple[float, float]:
        net_io = psutil.net_io_counters()
        return (net_io.bytes_sent, net_io.bytes_recv)

    def _format_bytes(self, bytes: float) -> str:
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB/s"

    def get_network_traffic(self) -> Tuple[str, str]:
        current_net_io = self._get_net_io()
        current_time = time.time()
        time_diff = current_time - self.last_net_time

        bytes_sent = (current_net_io[0] - self.last_net_io[0]) / time_diff
        bytes_recv = (current_net_io[1] - self.last_net_io[1]) / time_diff

        self.last_net_io = current_net_io
        self.last_net_time = current_time

        return (self._format_bytes(bytes_sent), self._format_bytes(bytes_recv))

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
        sent_speed, recv_speed = self.get_network_traffic()
        return {
            "user": f"{self.username}@{self.hostname}",
            "mem": self.get_memory_usage(),
            "cpu_temp": self.get_cpu_temp(),
            "load": self.get_load_average(),
            "net_send": sent_speed,
            "net_recv": recv_speed
        }