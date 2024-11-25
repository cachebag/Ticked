# src/ui/menu_handlers.py
import curses
import datetime
import time
from typing import List
from ..models.schedule import ClassSchedule
from ..models.week import Week
from ..utils.constants import BULLET, DAYS_OF_WEEK, STARTUP_MESSAGES, SHUTDOWN_MESSAGES
from .terminal import TerminalUI

class MenuHandlers:
    def __init__(self, ui: TerminalUI, schedule: ClassSchedule):
        self.ui = ui
        self.schedule = schedule

    def handle_assignments_view(self, week: Week, day_index: int):
        day_name = DAYS_OF_WEEK[day_index]
        assignments = week.assignments[day_index]
        selected_index = 0
        scroll_offset = 0
        visible_range = self.ui.height - 10

        self.ui.enter_input_mode()

        while True:
            if curses.is_term_resized(self.ui.height, self.ui.width):
                self.ui.update_dimensions()
                curses.resize_term(self.ui.height, self.ui.width)
                self.ui.stdscr.clear()

            self.ui.draw_assignment_list(day_name, assignments, selected_index, scroll_offset)
            key = self.ui.stdscr.getch()

            if key == ord('q'):
                break
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
                old_timeout = self.ui.stdscr.getch()
                self.ui.stdscr.nodelay(0)
                name = self.ui.get_input(f"Enter assignment for {day_name}:", 8)
                self.ui.stdscr.nodelay(1)
                if name:
                    week.add_assignment(day_index, name)
                    selected_index = len(assignments) - 1
            elif key == ord('d'):
                if assignments and 0 <= selected_index < len(assignments):
                    assignments.pop(selected_index)
                    if selected_index >= len(assignments):
                        selected_index = max(0, len(assignments) - 1)

        self.ui.enter_display_mode()

    def handle_day_menu(self, week: Week):
        day_index = 0
        
        while True:
            if curses.is_term_resized(self.ui.height, self.ui.width):
                self.ui.update_dimensions()
                curses.resize_term(self.ui.height, self.ui.width)
                self.ui.stdscr.clear()

            self.ui.stdscr.clear()
            self.ui.draw_border()
            self.ui.draw_status_bar()
            
            self.ui.center_text(5, f"[ Week {week.week_number} ]", color_pair=3, highlight=True)
            
            for i, day in enumerate(DAYS_OF_WEEK):
                if 7 + i * 2 >= self.ui.height - 3:
                    break
                
                color = 2 if i == day_index else 1
                day_text = f"{BULLET} {day}"
                assignment_count = len(week.assignments[i])
                if assignment_count > 0:
                    completed = sum(1 for a in week.assignments[i] if a.completed)
                    day_text += f" ({completed}/{assignment_count} completed)"
                
                self.ui.center_text(7 + i * 2, day_text, color_pair=color)
            
            self.ui.center_text(self.ui.height - 2, "[ ENTER: View Assignments | Q: Back ]", color_pair=3)
            
            self.ui.stdscr.refresh()
            key = self.ui.stdscr.getch()

            if key == -1:
                continue
            elif key == curses.KEY_UP:
                day_index = (day_index - 1) % 7
            elif key == curses.KEY_DOWN:
                day_index = (day_index + 1) % 7
            elif key in [curses.KEY_ENTER, 10, 13]:
                self.handle_assignments_view(week, day_index)
            elif key == ord('q'):
                break

    def handle_week_menu(self, semester):
        week_index = 0
        while True:
            if curses.is_term_resized(self.ui.height, self.ui.width):
                self.ui.update_dimensions()
                curses.resize_term(self.ui.height, self.ui.width)
                self.ui.stdscr.clear()

            options = [f"Week {i+1}" for i in range(14)]
            self.ui.draw_menu(f"Select Week - {semester.name}", options, week_index)
            key = self.ui.stdscr.getch()

            if key == -1:
                continue
            elif key == curses.KEY_UP:
                week_index = (week_index - 1) % 14
            elif key == curses.KEY_DOWN:
                week_index = (week_index + 1) % 14
            elif key in [curses.KEY_ENTER, 10, 13]:
                selected_week = semester.enter_week(week_index + 1)
                self.handle_day_menu(selected_week)
            elif key == ord('q'):
                break

    def handle_semester_menu(self):
        semester_list = self.schedule.view_schedule()
        if not semester_list:
            self.ui.display_message("No semesters found. Please add a semester first.")
            return

        index = 0
        while True:
            if curses.is_term_resized(self.ui.height, self.ui.width):
                self.ui.update_dimensions()
                curses.resize_term(self.ui.height, self.ui.width)
                self.ui.stdscr.clear()

            self.ui.draw_menu("Select Semester", semester_list, index)
            key = self.ui.stdscr.getch()

            if key == -1:
                continue
            elif key == curses.KEY_UP:
                index = (index - 1) % len(semester_list)
            elif key == curses.KEY_DOWN:
                index = (index + 1) % len(semester_list)
            elif key in [curses.KEY_ENTER, 10, 13]:
                selected_semester = self.schedule.semesters[semester_list[index]]
                self.handle_week_menu(selected_semester)
            elif key == ord('q'):
                break

    def handle_main_menu(self) -> bool:
        options = ["Add Semester", "View Schedule", "Exit ROBCO Terminal"]
        index = 0
        
        while True:
            if curses.is_term_resized(self.ui.height, self.ui.width):
                self.ui.update_dimensions()
                curses.resize_term(self.ui.height, self.ui.width)
                self.ui.stdscr.clear()

            self.ui.draw_menu("ROBCO INDUSTRIES UNIFIED OPERATING SYSTEM", options, index)
            key = self.ui.stdscr.getch()

            if key == -1:
                continue
            elif key == curses.KEY_UP:
                index = (index - 1) % len(options)
            elif key == curses.KEY_DOWN:
                index = (index + 1) % len(options)
            elif key in [curses.KEY_ENTER, 10, 13]:
                if index == 0:
                    self.ui.stdscr.nodelay(0)
                    semester_name = self.ui.get_input("Enter Semester Designation:", 8)
                    self.ui.stdscr.nodelay(1)
                    if semester_name:
                        start_date = datetime.date(2024, 1, 1)
                        self.schedule.add_semester(semester_name, start_date)
                        self.ui.display_message("Semester added successfully!")
                elif index == 1:
                    self.handle_semester_menu()
                elif index == 2:
                    return False
            elif key == ord('q'):
                return False
            
        return True

    def show_startup_sequence(self):
        for i, msg in enumerate(STARTUP_MESSAGES):
            self.ui.stdscr.clear()
            for j, line in enumerate(STARTUP_MESSAGES[:i+1]):
                self.ui.center_text(
                    self.ui.height//2 - len(STARTUP_MESSAGES)//2 + j, 
                    line, 
                    color_pair=1
                )
            self.ui.stdscr.refresh()
            time.sleep(0.5)
        time.sleep(1)

    def show_shutdown_sequence(self):
        for i, msg in enumerate(SHUTDOWN_MESSAGES):
            self.ui.stdscr.clear()
            for j, line in enumerate(SHUTDOWN_MESSAGES[:i+1]):
                self.ui.center_text(
                    self.ui.height//2 - len(SHUTDOWN_MESSAGES)//2 + j, 
                    line, 
                    color_pair=1
                )
            self.ui.stdscr.refresh()
            time.sleep(0.5)
