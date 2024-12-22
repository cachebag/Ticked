import curses
import time
import datetime
from .terminal import TerminalUI
from typing import List, Optional
from ..utils.constants import (
    STARTUP_MESSAGES, 
    SHUTDOWN_MESSAGES,
    BULLET
)
from ..models.task import Task, TaskType
from ..models.calendar import CalendarView

class MenuHandlers:
    def __init__(self, ui: TerminalUI):
        self.ui = ui

    def handle_main_menu(self) -> bool:
        options = ["add event", "notes", "pomodoro", "youtube", "spotify", "exit"]
        index = 0
    
        while True:
            if curses.is_term_resized(self.ui.height, self.ui.width):
                self.ui.update_dimensions()
                curses.resize_term(self.ui.height, self.ui.width)

            self.ui.draw_menu("TICK", options, index)
        
            key = self.ui.main_loop()
            if key is None:
                continue

            if key == curses.KEY_UP:
                index = (index - 1) % len(options)
            elif key == curses.KEY_DOWN:
                index = (index + 1) % len(options)
            elif key in [curses.KEY_ENTER, 10, 13]:
                if index == 0:  # add event
                    self.add_task()
                elif index == 1:  # notes
                    self.ui.display_message("Feature coming soon!")
                elif index == 2:  # pomodoro
                    self.ui.display_message("Feature coming soon!")
                elif index == 3:  # youtube
                    self.ui.display_message("Feature coming soon!")
                elif index == 4:  # spotify
                    self.ui.display_message("Feature coming soon!")
                elif index == 5:  # exit
                    return False
            elif key == ord('q'):
                self.ui.current_draw_function = None
                return False
    
        return True

    def show_startup_sequence(self):
        def center_text_fullscreen(y, text, color_pair=1):
            if y >= self.ui.height:
                return
            x = max(0, (self.ui.width - len(text)) // 2)
            try:
                self.ui.stdscr.addstr(y, x, text, curses.color_pair(color_pair))
            except curses.error:
                pass

        for i, msg in enumerate(STARTUP_MESSAGES):
            self.ui.stdscr.erase()
            start_y = self.ui.height//2 - len(STARTUP_MESSAGES)//2
            for j, line in enumerate(STARTUP_MESSAGES[:i+1]):
                center_text_fullscreen(start_y + j, line, color_pair=1)
            self.ui.stdscr.refresh()
            time.sleep(0.1)
        time.sleep(0)

    def show_shutdown_sequence(self):
        self.ui.current_draw_function = None
    
        for i, msg in enumerate(SHUTDOWN_MESSAGES):
            self.ui.stdscr.erase()
            start_y = self.ui.height//2 - len(SHUTDOWN_MESSAGES)//2
        
            for j, line in enumerate(SHUTDOWN_MESSAGES[:i+1]):
                x = max(0, (self.ui.width - len(line)) // 2)
                try:
                    self.ui.stdscr.addstr(start_y + j, x, line, curses.color_pair(1))
                except curses.error:
                    pass
        
            self.ui.stdscr.refresh()
            time.sleep(0.1)

    def add_task(self) -> None:
        """Handle task creation interface"""
        # First, let user select a date from calendar if they haven't already
        selected_date = None
        
        # Save previous state
        prev_draw_function = self.ui.current_draw_function
        prev_draw_args = self.ui.current_draw_args
        
        while selected_date is None:
            self.ui.stdscr.erase()
            self.ui.draw_border()
            self.ui.draw_status_bar()
            
            # Draw instructions at the top of the window
            instructions = [
                "[ Calendar Navigation ]",
                "↑/↓/←/→: Move selection",
                "Enter: Select date",
                "Q: Cancel"
            ]
            
            # Draw each instruction line
            for i, instruction in enumerate(instructions):
                self.ui.center_text(4 + i, instruction, 
                                  color_pair=3 if i == 0 else 1, 
                                  highlight=(i == 0))
            
            # Draw calendar with more space at the top for instructions
            self.ui.calendar_view.draw(
                self.ui, 
                self.ui.sidebar_width + 1,
                4 + len(instructions) + 1,
                self.ui.width - self.ui.sidebar_width - 1,
                self.ui.height - (4 + len(instructions) + 1)
            )
            
            self.ui.stdscr.refresh()
            
            # Get input without nodelay
            self.ui.stdscr.nodelay(0)
            key = self.ui.stdscr.getch()
            self.ui.stdscr.nodelay(1)
            
            if key is None:
                continue
            
            continue_calendar, date = self.ui.calendar_view.handle_input(key)
            if not continue_calendar:
                if date is None:  # User pressed Q to quit
                    # Restore previous state
                    self.ui.current_draw_function = prev_draw_function
                    self.ui.current_draw_args = prev_draw_args
                    return
                selected_date = date
                break
        
        # Restore previous state
        self.ui.current_draw_function = prev_draw_function
        self.ui.current_draw_args = prev_draw_args
        
        if selected_date is None:
            return
            
        # Continue with rest of task creation...
        title = self.ui.get_input("Enter task title:", 6)
        if not title:
            return
            
        # Task type selection
        type_options = ["Assignment", "Exam", "Appointment", "Meeting", "Deadline", "Other"]
        selected_type = self.get_selection("Select task type:", type_options)
        if selected_type is None:
            return
        task_type = TaskType.from_string(type_options[selected_type])
            
        # Time input (optional)
        time_str = self.ui.get_input("Enter time (HH:MM) or leave blank:", 10)
        task_time = None
        if time_str:
            try:
                hour, minute = map(int, time_str.split(':'))
                task_time = datetime.time(hour, minute)
            except (ValueError, TypeError):
                self.ui.display_message("Invalid time format. Using no time.", wait=True)
            
        # Description (optional)
        description = self.ui.get_input("Enter description (optional):", 12)
            
        # Create task
        task = Task(
            title=title,
            date=datetime.datetime.combine(selected_date, task_time or datetime.time()),
            task_type=task_type,
            time=task_time,
            description=description
        )
            
        # Add task and confirm
        if hasattr(self.ui.calendar_view, 'add_task'):
            self.ui.calendar_view.add_task(task)
        self.ui.display_message("Task added successfully!", wait=True)

    def get_selection(self, prompt: str, options: List[str]) -> Optional[int]:
        """Get user selection from a list of options"""
        selected = 0
        
        # Save previous state
        prev_draw_function = self.ui.current_draw_function
        prev_draw_args = self.ui.current_draw_args
        
        while True:
            self.ui.stdscr.erase()
            self.ui.draw_border()
            self.ui.draw_status_bar()
            
            # Draw prompt
            self.ui.center_text(5, f"[ {prompt} ]", color_pair=3, highlight=True)
            
            # Draw options
            for i, option in enumerate(options):
                if 7 + i >= self.ui.height - 1:
                    break
                color = 2 if i == selected else 1
                self.ui.center_text(7 + i, f"{BULLET} {option}", color_pair=color)
            
            self.ui.stdscr.refresh()
            
            # Get input without nodelay
            self.ui.stdscr.nodelay(0)
            key = self.ui.stdscr.getch()
            self.ui.stdscr.nodelay(1)
            
            if key == curses.KEY_UP:
                selected = (selected - 1) % len(options)
            elif key == curses.KEY_DOWN:
                selected = (selected + 1) % len(options)
            elif key in [curses.KEY_ENTER, 10, 13]:
                # Restore previous state
                self.ui.current_draw_function = prev_draw_function
                self.ui.current_draw_args = prev_draw_args
                return selected
            elif key == ord('q'):
                # Restore previous state
                self.ui.current_draw_function = prev_draw_function
                self.ui.current_draw_args = prev_draw_args
                return None
            
            self.ui.stdscr.refresh()
