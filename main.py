import datetime
import curses
import textwrap
import time
from enum import Enum
import psutil
import socket
import os
from typing import Dict, List, Tuple
from class_schedule import ClassSchedule

CHECK_MARK = "*"
CROSS_MARK = " "
BULLET = ">"
CURSOR = "_"
ACTIVE_DOT = "●"

class MenuState(Enum):
    MAIN = 1
    SEMESTER = 2
    WEEK = 3
    DAY = 4
    ASSIGNMENTS = 5

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

class TerminalUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.setup_colors()
        curses.curs_set(0)
        self.status_bar = StatusBar()
        self.update_dimensions()
        self.stdscr.timeout(500)

    def setup_colors(self):
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    def update_dimensions(self):
        self.height, self.width = self.stdscr.getmaxyx()

    def draw_status_bar(self):
        sys_info = self.status_bar.system_monitor.get_system_info()
        
        user_info = f"USER: {sys_info['user']}"
        size_info = f"TERMINAL: {self.width}x{self.height}"
        connection = f"CONNECTION: {ACTIVE_DOT} ACTIVE" if self.status_bar.should_blink_cursor() else "CONNECTION: ○ ACTIVE"
        self.safe_addstr(0, 2, user_info, curses.color_pair(1) | curses.A_DIM)
        self.safe_addstr(0, len(user_info) + 4, size_info, curses.color_pair(1) | curses.A_DIM)
        self.safe_addstr(0, self.width - len(connection) - 2, connection, curses.color_pair(1) | curses.A_DIM)

        mem_info = f"MEM: {sys_info['mem']}"
        cpu_temp = f"CPU TEMP: {sys_info['cpu_temp']}"
        load_avg = f"LOAD: {sys_info['load']}"
        self.safe_addstr(1, 2, mem_info, curses.color_pair(1) | curses.A_DIM)
        self.safe_addstr(1, len(mem_info) + 4, cpu_temp, curses.color_pair(1) | curses.A_DIM)
        self.safe_addstr(1, len(mem_info) + len(cpu_temp) + 6, load_avg, curses.color_pair(1) | curses.A_DIM)

        net_info = f"NET ↑: {sys_info['net_send']} ↓: {sys_info['net_recv']}"
        uptime = f"UPTIME: {self.status_bar.get_uptime()}"
        self.safe_addstr(2, 2, net_info, curses.color_pair(1) | curses.A_DIM)
        self.safe_addstr(2, self.width - len(uptime) - 2, uptime, curses.color_pair(1) | curses.A_DIM)

        if self.status_bar.should_blink_cursor():
            self.safe_addstr(2, self.width - 1, CURSOR, curses.color_pair(1) | curses.A_BOLD)

    def safe_addstr(self, y, x, text, attr=0):
        try:
            if y < self.height and x < self.width:
                max_length = self.width - x
                if max_length > 0:
                    self.stdscr.addstr(y, x, text[:max_length], attr)
        except curses.error:
            pass

    def draw_border(self):
        try:
            for x in range(self.width - 1):
                self.safe_addstr(3, x, "-", curses.color_pair(1))
                self.safe_addstr(self.height - 1, x, "-", curses.color_pair(1))
            for y in range(3, self.height):
                self.safe_addstr(y, 0, "|", curses.color_pair(1))
                self.safe_addstr(y, self.width - 1, "|", curses.color_pair(1))
        except curses.error:
            pass

    def center_text(self, y, text, color_pair=1, highlight=False):
        if y >= self.height:
            return
        x = max(1, (self.width - len(text)) // 2)
        attr = curses.A_BOLD if highlight else curses.A_NORMAL
        self.safe_addstr(y, x, text, curses.color_pair(color_pair) | attr)

    def draw_menu(self, title, options, selected_index, start_y=7):
        self.stdscr.clear()
        self.draw_border()
        self.draw_status_bar()
        
        title_text = f"[ {title} ]"
        self.center_text(5, title_text, color_pair=3, highlight=True)
        
        for i, option in enumerate(options):
            if start_y + i * 2 >= self.height - 1:
                break
            color = 2 if i == selected_index else 1
            text = f"{BULLET} {option}"
            self.center_text(start_y + i * 2, text, color_pair=color)

        self.center_text(self.height - 2, "[ UP/DOWN: Navigate | ENTER: Select | Q: Back ]", color_pair=3)
        self.stdscr.refresh()

    def draw_assignment_list(self, day_name, assignments, selected_index, scroll_offset=0):
        self.stdscr.clear()
        self.draw_border()
        self.draw_status_bar()
        
        title = f"[ {day_name} Assignments ]"
        self.center_text(5, title, color_pair=3, highlight=True)
        
        visible_range = self.height - 10
        total_assignments = len(assignments)
        
        max_scroll = max(0, total_assignments - visible_range)
        scroll_offset = max(0, min(scroll_offset, max_scroll))
        
        display_assignments = assignments[scroll_offset:scroll_offset + visible_range]
        for i, assignment in enumerate(display_assignments):
            color = 2 if i + scroll_offset == selected_index else 1
            self.center_text(i + 7, str(assignment), color_pair=color)

        controls = "[ UP/DOWN: Navigate | SPACE: Toggle | A: Add | D: Delete | Q: Back ]"
        self.center_text(self.height - 2, controls, color_pair=3)
        
        if total_assignments > visible_range:
            scroll_info = f"Showing {scroll_offset + 1}-{min(scroll_offset + visible_range, total_assignments)} of {total_assignments}"
            self.center_text(self.height - 3, scroll_info, color_pair=1)
        
        self.stdscr.refresh()

    def get_input(self, prompt, y_pos):
        self.stdscr.clear()
        self.draw_border()
        self.draw_status_bar()
        self.center_text(y_pos, prompt, color_pair=3)
        
        curses.echo()
        input_y = min(y_pos + 2, self.height - 2)
        input_x = (self.width - 30) // 2
        self.stdscr.move(input_y, input_x)
        
        try:
            input_str = self.stdscr.getstr(input_y, input_x, 30).decode("utf-8")
        except curses.error:
            input_str = ""
        curses.noecho()
        
        return input_str

    def display_message(self, message, wait=True):
        self.stdscr.clear()
        self.draw_border()
        self.draw_status_bar()
        self.center_text(self.height // 2, message, color_pair=3)
        self.stdscr.refresh()
        if wait:
            self.stdscr.getch()

def main(stdscr):
    ui = TerminalUI(stdscr)
    schedule = ClassSchedule()

    def handle_assignments_view(week, day_index):
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        day_name = days[day_index]
        assignments = week.assignments[day_index]
        selected_index = 0
        scroll_offset = 0
        visible_range = ui.height - 10

        while True:
            if curses.is_term_resized(ui.height, ui.width):
                ui.update_dimensions()
                curses.resize_term(ui.height, ui.width)
                stdscr.clear()

            ui.draw_assignment_list(day_name, assignments, selected_index, scroll_offset)
            key = stdscr.getch()

            if key == -1:
                continue
            elif key == curses.KEY_UP:
                if selected_index > 0:
                    selected_index -= 1
                    if selected_index < scroll_offset:
                        scroll_offset = selected_index
            elif key == curses.KEY_DOWN:
                if selected_index < len(assignments) - 1:
                    selected_index += 1
                    if selected_index >= scroll_offset + visible_range:
                        scroll_offset = selected_index - visible_range + 1
            elif key == ord(' '):
                if assignments:
                    week.toggle_assignment_completion(day_index, selected_index)
            elif key == ord('a'):
                name = ui.get_input(f"Enter assignment for {day_name}:", 8)
                if name:
                    week.add_assignment(day_index, name)
                    selected_index = len(assignments) - 1
            elif key == ord('d'):
                if assignments and 0 <= selected_index < len(assignments):
                    assignments.pop(selected_index)
                    if selected_index >= len(assignments):
                        selected_index = max(0, len(assignments) - 1)
            elif key == ord('q'):
                break

    def handle_main_menu():
        options = ["Add Semester", "View Schedule", "Exit ROBCO Terminal"]
        index = 0
        
        while True:
            if curses.is_term_resized(ui.height, ui.width):
                ui.update_dimensions()
                curses.resize_term(ui.height, ui.width)
                stdscr.clear()

            ui.draw_menu("ROBCO INDUSTRIES UNIFIED OPERATING SYSTEM", options, index)
            key = stdscr.getch()

            if key == -1:
                continue
            elif key == curses.KEY_UP:
                index = (index - 1) % len(options)
            elif key == curses.KEY_DOWN:
                index = (index + 1) % len(options)
            elif key in [curses.KEY_ENTER, 10, 13]:
                if index == 0:
                    semester_name = ui.get_input("Enter Semester Designation:", 8)
                    if semester_name:
                        start_date = datetime.date(2024, 1, 1)
                        schedule.add_semester(semester_name, start_date)
                        ui.display_message("Semester added successfully!")
                elif index == 1:
                    handle_semester_menu()
                elif index == 2:
                    return False
            elif key == ord('q'):
                return False
            
        return True

    def handle_semester_menu():
        semester_list = schedule.view_schedule()
        if not semester_list:
            ui.display_message("No semesters found. Please add a semester first.")
            return

        index = 0
        while True:
            if curses.is_term_resized(ui.height, ui.width):
                ui.update_dimensions()
                curses.resize_term(ui.height, ui.width)
                stdscr.clear()

            ui.draw_menu("Select Semester", semester_list, index)
            key = stdscr.getch()

            if key == -1:
                continue
            elif key == curses.KEY_UP:
                index = (index - 1) % len(semester_list)
            elif key == curses.KEY_DOWN:
                index = (index + 1) % len(semester_list)
            elif key in [curses.KEY_ENTER, 10, 13]:
                selected_semester = schedule.semesters[semester_list[index]]
                handle_week_menu(selected_semester)
            elif key == ord('q'):
                break

    def handle_week_menu(semester):
        week_index = 0
        while True:
            if curses.is_term_resized(ui.height, ui.width):
                ui.update_dimensions()
                curses.resize_term(ui.height, ui.width)
                stdscr.clear()

            options = [f"Week {i+1}" for i in range(14)]
            ui.draw_menu(f"Select Week - {semester.name}", options, week_index)
            key = stdscr.getch()

            if key == -1:
                continue
            elif key == curses.KEY_UP:
                week_index = (week_index - 1) % 14
            elif key == curses.KEY_DOWN:
                week_index = (week_index + 1) % 14
            elif key in [curses.KEY_ENTER, 10, 13]:
                selected_week = semester.enter_week(week_index + 1)
                handle_day_menu(selected_week)
            elif key == ord('q'):
                break

    def handle_day_menu(week):
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        day_index = 0
        
        while True:
            if curses.is_term_resized(ui.height, ui.width):
                ui.update_dimensions()
                curses.resize_term(ui.height, ui.width)
                stdscr.clear()

            ui.stdscr.clear()
            ui.draw_border()
            ui.draw_status_bar()
            
            ui.center_text(5, f"[ Week {week.week_number} ]", color_pair=3, highlight=True)
            
            for i, day in enumerate(days):
                if 7 + i * 2 >= ui.height - 3:
                    break
                
                color = 2 if i == day_index else 1
                day_text = f"{BULLET} {day}"
                assignment_count = len(week.assignments[i])
                if assignment_count > 0:
                    completed = sum(1 for a in week.assignments[i] if a.completed)
                    day_text += f" ({completed}/{assignment_count} completed)"
                
                ui.center_text(7 + i * 2, day_text, color_pair=color)
            
            ui.center_text(ui.height - 2, "[ ENTER: View Assignments | Q: Back ]", color_pair=3)
            
            ui.stdscr.refresh()
            key = stdscr.getch()

            if key == -1:
                continue
            elif key == curses.KEY_UP:
                day_index = (day_index - 1) % 7
            elif key == curses.KEY_DOWN:
                day_index = (day_index + 1) % 7
            elif key in [curses.KEY_ENTER, 10, 13]:
                handle_assignments_view(week, day_index)
            elif key == ord('q'):
                break

    startup_msg = [
        "ROBCO INDUSTRIES UNIFIED OPERATING SYSTEM v1.0",
        f"COPYRIGHT 2024-2025 ROBCO INDUSTRIES",
        "LOADER V1.1",
        "EXEC VERSION 41.10",
        "-SERVER 1-"
    ]
    
    for i, msg in enumerate(startup_msg):
        stdscr.clear()
        for j, line in enumerate(startup_msg[:i+1]):
            ui.center_text(ui.height//2 - len(startup_msg)//2 + j, line, color_pair=1)
        stdscr.refresh()
        time.sleep(0.5)
    
    time.sleep(1)

    try:
        while True:
            if not handle_main_menu():
                break
    except KeyboardInterrupt:
        pass

    shutdown_msg = [
        "SHUTTING DOWN ROBCO TERMINAL",
        "SAVING SESSION DATA...",
        "CLEARING MEMORY...",
        "GOODBYE."
    ]
    
    for i, msg in enumerate(shutdown_msg):
        stdscr.clear()
        for j, line in enumerate(shutdown_msg[:i+1]):
            ui.center_text(ui.height//2 - len(shutdown_msg)//2 + j, line, color_pair=1)
        stdscr.refresh()
        time.sleep(0.5)

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
