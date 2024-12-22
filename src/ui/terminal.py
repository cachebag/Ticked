#terminal 

import curses
import time
from typing import List, Optional, Callable
from .status_bar import StatusBar
from ..utils.constants import ACTIVE_DOT, CURSOR, BULLET
from ..models.calendar import CalendarView

class TerminalUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.setup_colors()
        curses.curs_set(0)
        self.status_bar = StatusBar()
        self.update_dimensions()
        self.sidebar_width = 30
        self.last_refresh = 0
        self.refresh_interval = 1.0  # Refresh every 500ms
        self.current_draw_function: Optional[Callable] = None
        self.current_draw_args: tuple = ()
        self.calendar_view = CalendarView()

    def setup_colors(self):
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)

    def enter_input_mode(self):
        self.stdscr.nodelay(0)

    def enter_display_mode(self):
        self.stdscr.nodelay(1)

    def update_dimensions(self):
        self.height, self.width = self.stdscr.getmaxyx()
        self.sidebar_width = min(30, self.width // 3)

    def schedule_refresh(self, draw_function: Callable, *args):
        """Schedule a drawing function to be called on refresh"""
        self.current_draw_function = draw_function
        self.current_draw_args = args

    def check_refresh(self):
        """Check if it's time to refresh and update if needed"""
        current_time = time.time()
        if current_time - self.last_refresh >= self.refresh_interval:
            self.last_refresh = current_time
            if self.current_draw_function:
                self.current_draw_function(*self.current_draw_args)
            else:
                self.stdscr.refresh()

    def draw_status_bar(self):
        sys_info = self.status_bar.system_monitor.get_system_info()
        
        # Top status bar
        user_info = f"USER: {sys_info['user']}"
        size_info = f"TERMINAL: {self.width}x{self.height}"
        connection = f"CONNECTION: {ACTIVE_DOT} ACTIVE" if self.status_bar.should_blink_cursor() else "CONNECTION: ○ ACTIVE"
        self.safe_addstr(0, 2, user_info, curses.color_pair(1) | curses.A_DIM)
        self.safe_addstr(0, len(user_info) + 4, size_info, curses.color_pair(1) | curses.A_DIM)
        self.safe_addstr(0, self.width - len(connection) - 2, connection, curses.color_pair(1) | curses.A_DIM)

        # System info
        mem_info = f"MEM: {sys_info['mem']}"
        cpu_temp = f"CPU TEMP: {sys_info['cpu_temp']}"
        load_avg = f"LOAD: {sys_info['load']}"
        self.safe_addstr(1, 2, mem_info, curses.color_pair(1) | curses.A_DIM)
        self.safe_addstr(1, len(mem_info) + 4, cpu_temp, curses.color_pair(1) | curses.A_DIM)
        self.safe_addstr(1, len(mem_info) + len(cpu_temp) + 6, load_avg, curses.color_pair(1) | curses.A_DIM)

        # Uptime
        uptime = f"UPTIME: {self.status_bar.get_uptime()}"
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
                self.safe_addstr(3, x, "-", curses.color_pair(1))  # Top border
                self.safe_addstr(self.height - 1, x, "-", curses.color_pair(1))  # Bottom border

            for y in range(3, self.height):
                self.safe_addstr(y, 0, "|", curses.color_pair(1))  # Left border
                self.safe_addstr(y, self.sidebar_width, "|", curses.color_pair(1))  # Sidebar separator
                self.safe_addstr(y, self.width - 1, "|", curses.color_pair(1))  # Right border
        except curses.error:
            pass

    def center_text(self, y, text, color_pair=1, highlight=False, main_content=True):
        if y >= self.height:
            return
        
        if main_content:
            content_width = self.width - self.sidebar_width - 2
            x = self.sidebar_width + 1 + (content_width - len(text)) // 2
        else:
            x = 1 + (self.sidebar_width - len(text)) // 2
            
        attr = curses.A_BOLD if highlight else curses.A_NORMAL
        self.safe_addstr(y, x, text, curses.color_pair(color_pair) | attr)

    def draw_menu(self, title: str, options: List[str], selected_index: int, start_y: int = 7):
        self.schedule_refresh(self.draw_menu, title, options, selected_index, start_y)
    
        self.stdscr.erase()
        self.draw_border()
        self.draw_status_bar()
    
        # Draw sidebar menu
        sidebar_title = "[ MENU ]"
        self.center_text(5, sidebar_title, color_pair=3, highlight=True, main_content=False)
    
        for i, option in enumerate(options):
            if start_y + i * 2 >= self.height - 1:
                break
            color = 2 if i == selected_index else 1
            text = f"{BULLET} {option}"
            if len(text) > self.sidebar_width - 4:
                text = text[:self.sidebar_width - 7] + "..."
            self.center_text(start_y + i * 2, text, color_pair=color, main_content=False)
    
        # Draw calendar in main content area
        main_x = self.sidebar_width + 1
        main_width = self.width - main_x - 1
        main_height = self.height - 4  # Account for borders
        self.calendar_view.draw(self, main_x, 4, main_width, main_height)
    
        # Draw controls
        controls = "[ ↑/↓: Navigate | ENTER: Select | Q: Exit ]"
        self.center_text(self.height - 2, controls, color_pair=3)
    
        self.stdscr.refresh()

    def draw_assignment_list(self, day_name: str, assignments: List[str], selected_index: int, scroll_offset: int = 0):
        self.schedule_refresh(self.draw_assignment_list, day_name, assignments, selected_index, scroll_offset)
        
        self.stdscr.erase()
        self.draw_border()
        self.draw_status_bar()
        
        sidebar_title = "[ ASSIGNMENTS ]"
        self.center_text(5, sidebar_title, color_pair=3, highlight=True, main_content=False)
        
        title = f"[ {day_name} ]"
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

    def get_input(self, prompt: str, y_pos: int) -> str:
        prev_draw_function = self.current_draw_function
        prev_draw_args = self.current_draw_args
        self.current_draw_function = None
    
        self.stdscr.erase()
        self.draw_border()
        self.draw_status_bar()
    
        self.center_text(y_pos, prompt, color_pair=3)
    
        input_y = min(y_pos + 2, self.height - 2)
        main_content_center = self.sidebar_width + (self.width - self.sidebar_width) // 2
        input_x = main_content_center - 15
    
        curses.curs_set(1)
        curses.echo()
    
        self.stdscr.nodelay(0)
    
        try:
            self.stdscr.move(input_y, input_x)
            input_str = self.stdscr.getstr(input_y, input_x, 30).decode('utf-8')
        except curses.error:
            input_str = ""
        finally:
            curses.curs_set(0)
            curses.noecho()
            self.stdscr.nodelay(1)
            self.current_draw_function = prev_draw_function
            self.current_draw_args = prev_draw_args
    
        return input_str.strip()

    def display_message(self, message: str, wait: bool = True):
        if wait:
            prev_draw_function = self.current_draw_function
            prev_draw_args = self.current_draw_args
            self.current_draw_function = None
        
        self.stdscr.erase()
        self.draw_border()
        self.draw_status_bar()

        lines = message.split('\n')
        start_y = (self.height - len(lines)) // 2

        for i, line in enumerate(lines):
            self.center_text(start_y + i, line, color_pair=3, main_content=True)

        if wait:
            self.enter_input_mode()
            self.stdscr.getch()
            self.enter_display_mode()
            self.current_draw_function = prev_draw_function
            self.current_draw_args = prev_draw_args

    def main_loop(self):
        """Main event loop that handles both user input and refresh"""
        try:
            # Set a shorter sleep time
            time.sleep(0.001)
            
            # Only refresh if needed
            current_time = time.time()
            if current_time - self.last_refresh >= 0.1:  # Reduce refresh interval to 100ms
                if self.current_draw_function:
                    self.current_draw_function(*self.current_draw_args)
                self.last_refresh = current_time
            
            # Check for input
            key = self.stdscr.getch()
            if key != curses.ERR:
                # Force refresh on key press
                if self.current_draw_function:
                    self.current_draw_function(*self.current_draw_args)
                return key
            
            return None
            
        except KeyboardInterrupt:
            return ord('q')
        except curses.error:
            return None
