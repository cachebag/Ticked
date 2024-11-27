import curses
from typing import List
from .status_bar import StatusBar
from ..utils.constants import ACTIVE_DOT, CURSOR, BULLET

class TerminalUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.setup_colors()
        curses.curs_set(0)
        self.status_bar = StatusBar()
        self.update_dimensions()

    def setup_colors(self):
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    def enter_input_mode(self):
        self.stdscr.nodelay(0)

    def enter_display_mode(self):
        self.stdscr.nodelay(1)

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
            # src/ui/terminal.py (continued)
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
        finally:
            curses.noecho()
        
        return input_str

    def display_message(self, message, wait=True):
        self.stdscr.clear()
        self.draw_border()
        self.draw_status_bar()
        self.center_text(self.height // 2, message, color_pair=3)
        self.stdscr.refresh()
        if wait:
            self.enter_input_mode()
            self.stdscr.getch()
            self.enter_display_mode()
