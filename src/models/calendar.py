import calendar
import datetime
from typing import Dict, List, Optional, Tuple, Callable
import curses
from ..models.task import Task, TaskType

class DayView:
    def __init__(self, date: datetime.date, tasks: List[Task], add_task_callback: Optional[Callable] = None):
        self.date = date
        self.tasks = tasks
        self.selected_index = 0 if tasks else -1
        self.add_task_callback = add_task_callback
        self.show_menu = False
        self.menu_options = ["Add New Event", "Toggle Complete", "Back to Calendar"]
        self.menu_selected = 0

    def draw(self, ui, start_x: int, start_y: int, width: int, height: int):
        # Draw header
        date_str = self.date.strftime("%B %d, %Y")
        header = f"[ {date_str} ]"
        ui.center_text(start_y, header, color_pair=3, highlight=True)

        if not self.tasks:
            ui.center_text(start_y + 3, "No tasks for this day", color_pair=1)
            ui.center_text(start_y + 5, "Press 'a' to add a new event", color_pair=3)
            return

        # If showing menu overlay
        if self.show_menu:
            menu_y = (height - len(self.menu_options)) // 2
            ui.center_text(menu_y - 2, "[ Options ]", color_pair=3, highlight=True)
            for i, option in enumerate(self.menu_options):
                color = 2 if i == self.menu_selected else 1
                ui.center_text(menu_y + i, f"> {option}", color_pair=color)
            return

        # Draw tasks
        task_start_y = start_y + 3
        for i, task in enumerate(self.tasks):
            if task_start_y + i >= height - 3:  # Leave space for controls
                break

            # Highlight selected task
            color = 2 if i == self.selected_index else task.color_pair
            attr = curses.A_BOLD if i == self.selected_index else curses.A_NORMAL
            
            # Format time
            time_str = task.time.strftime("%H:%M") if task.time else "--:--"
            
            # Format title with completion status
            title = task.title
            if hasattr(task, 'completed') and task.completed:
                title = f"[✓] {title}"
            else:
                title = f"[ ] {title}"

            # Draw task header (time, type, and title)
            task_header = f"{time_str} - {task.task_type.name}: {title}"
            ui.safe_addstr(task_start_y + i*3, start_x + 2, task_header, 
                          curses.color_pair(color) | attr)

            # Draw description if it exists
            if task.description:
                desc = task.description
                # Wrap description if it's too long
                if len(desc) > width - 4:
                    desc = desc[:width - 7] + "..."
                ui.safe_addstr(task_start_y + i*3 + 1, start_x + 4, desc, 
                             curses.color_pair(1))

        # Draw controls
        if self.show_menu:
            controls = "[ ↑/↓: Navigate | ENTER: Select | ESC: Back ]"
        else:
            controls = "[ ↑/↓: Navigate | SPACE: Toggle | ENTER: Menu | A: Add | Q: Back ]"
        ui.center_text(height - 2, controls, color_pair=3)

    def handle_input(self, key) -> bool:
        """Handle input for day view. Returns True if should stay in day view."""
        if self.show_menu:
            return self._handle_menu_input(key)
            
        if key == ord('a'):
            if self.add_task_callback:
                return False, self.date
            return True
            
        if not self.tasks:
            if key in [ord('q'), curses.KEY_LEFT]:
                return False
            return True

        if key == curses.KEY_UP:
            self.selected_index = (self.selected_index - 1) % len(self.tasks)
        elif key == curses.KEY_DOWN:
            self.selected_index = (self.selected_index + 1) % len(self.tasks)
        elif key == ord(' '):  # Space to toggle completion
            if 0 <= self.selected_index < len(self.tasks):
                task = self.tasks[self.selected_index]
                if not hasattr(task, 'completed'):
                    setattr(task, 'completed', True)
                else:
                    task.completed = not task.completed
        elif key in [curses.KEY_ENTER, 10, 13]:  # Enter to show menu
            self.show_menu = True
            self.menu_selected = 0
        elif key in [ord('q'), curses.KEY_LEFT]:
            return False
        return True

    def _handle_menu_input(self, key) -> bool:
        """Handle input when menu is shown"""
        if key == 27:  # ESC key
            self.show_menu = False
            return True
            
        if key == curses.KEY_UP:
            self.menu_selected = (self.menu_selected - 1) % len(self.menu_options)
        elif key == curses.KEY_DOWN:
            self.menu_selected = (self.menu_selected + 1) % len(self.menu_options)
        elif key in [curses.KEY_ENTER, 10, 13]:
            self.show_menu = False
            if self.menu_selected == 0:  # Add New Event
                if self.add_task_callback:
                    self.add_task_callback(self.date)
            elif self.menu_selected == 1:  # Toggle Complete
                if 0 <= self.selected_index < len(self.tasks):
                    task = self.tasks[self.selected_index]
                    if not hasattr(task, 'completed'):
                        setattr(task, 'completed', True)
                    else:
                        task.completed = not task.completed
            elif self.menu_selected == 2:  # Back to Calendar
                return False
        return True

class CalendarView:
    def __init__(self):
        self.today = datetime.date.today()
        self.calendar = calendar.monthcalendar(self.today.year, self.today.month)
        self.selected_day = self.today.day
        self.weekday_abbr = ['M', 'T', 'W', 'Th', 'F', 'Sa', 'Su']
        self.tasks: Dict[datetime.date, List[Task]] = {}
        self.day_view: Optional[DayView] = None
        self.return_to_day_view = False
        self.last_viewed_date = None

    def draw(self, ui, start_x: int, start_y: int, width: int, height: int):
        """Draw either the calendar grid or day view"""
        if self.day_view is not None:
            self.day_view.draw(ui, start_x, start_y, width, height)
            return

        # Draw calendar grid
        cell_width = width // 7
        cell_height = (height - 3) // 6

        # Draw month and year header
        month_year = f"{self.today.strftime('%B %Y')}"
        header_x = start_x + (width - len(month_year)) // 2
        ui.safe_addstr(start_y, header_x, month_year, curses.color_pair(3) | curses.A_BOLD)
        
        # Draw weekday headers
        for i, day in enumerate(self.weekday_abbr):
            x = start_x + (i * cell_width) + 2
            ui.safe_addstr(start_y + 2, x, day, curses.color_pair(1) | curses.A_BOLD)
        
        # Draw calendar grid
        grid_start_y = start_y + 4
        for week_num, week in enumerate(self.calendar):
            for day_num, day in enumerate(week):
                if day != 0:
                    x = start_x + (day_num * cell_width)
                    y = grid_start_y + (week_num * cell_height)
                    
                    # Draw cell borders
                    border_color = curses.color_pair(6) if day == self.selected_day else curses.color_pair(1)
                    
                    # Draw borders
                    ui.safe_addstr(y, x, "┌" + "─" * (cell_width-2) + "┐", border_color)
                    for i in range(1, cell_height-1):
                        ui.safe_addstr(y + i, x, "│", border_color)
                        ui.safe_addstr(y + i, x + cell_width - 1, "│", border_color)
                    ui.safe_addstr(y + cell_height - 1, x, "└" + "─" * (cell_width-2) + "┘", border_color)
                    
                    # Determine day number color and attributes
                    if day == self.selected_day:
                        attr = curses.color_pair(5) | curses.A_BOLD
                    elif day == self.today.day:
                        attr = curses.color_pair(2) | curses.A_BOLD
                    else:
                        attr = curses.color_pair(1)
                    
                    # Draw day number
                    day_text = f"{day:2d}"
                    day_x = x + 2
                    ui.safe_addstr(y + 1, day_x, day_text, attr)

                    # Draw tasks for this day
                    current_date = datetime.date(self.today.year, self.today.month, day)
                    if current_date in self.tasks:
                        self._draw_tasks(ui, x + 1, y + 2, cell_width - 2, cell_height - 3, self.tasks[current_date])

    def _draw_tasks(self, ui, x: int, y: int, width: int, height: int, tasks: List[Task]):
        """Draw tasks within a calendar cell"""
        max_tasks = height  # Maximum number of tasks that can fit
        for i, task in enumerate(tasks[:max_tasks]):
            if y + i >= ui.height - 1:  # Prevent drawing outside screen
                break

            # Format task time
            time_str = task.time.strftime("%H:%M") if task.time else "--:--"
            
            # Format type indicator
            type_indicator = task.task_type.name[0]
            
            # Format title (truncate if necessary)
            max_title_len = width - len(time_str) - 4  # Account for time and type
            title = task.title[:max_title_len] + ('...' if len(task.title) > max_title_len else '')
            
            # Add completion status
            if hasattr(task, 'completed') and task.completed:
                title = f"✓{title}"
            
            # Combine everything
            task_text = f"{time_str} {type_indicator}:{title}"
            task_text = task_text[:width]  # Ensure it fits within cell width
            
            # Draw with appropriate color and strike-through if completed
            attr = curses.A_NORMAL
            if hasattr(task, 'completed') and task.completed:
                attr |= curses.A_DIM
            ui.safe_addstr(y + i, x, task_text, curses.color_pair(task.color_pair) | attr)

        # If there are more tasks than can fit, show indicator
        if len(tasks) > max_tasks:
            ui.safe_addstr(y + max_tasks - 1, x + width - 3, "...", curses.color_pair(1))

    def handle_input(self, key) -> Tuple[bool, Optional[datetime.date]]:
        """Handle calendar navigation input"""
        # If in day view, handle that first
        if self.day_view is not None:
            result = self.day_view.handle_input(key)
            if isinstance(result, tuple):
                self.day_view = None
                self.return_to_day_view = True
                return result
            if not result:
                self.day_view = None
            return True, None

        # Handle calendar navigation
        if key in [curses.KEY_LEFT, ord('h')]:
            self.selected_day = max(1, self.selected_day - 1)
        elif key in [curses.KEY_RIGHT, ord('l')]:
            last_day = calendar.monthrange(self.today.year, self.today.month)[1]
            self.selected_day = min(last_day, self.selected_day + 1)
        elif key in [curses.KEY_UP, ord('k')]:
            self.selected_day = max(1, self.selected_day - 7)
        elif key in [curses.KEY_DOWN, ord('j')]:
            last_day = calendar.monthrange(self.today.year, self.today.month)[1]
            self.selected_day = min(last_day, self.selected_day + 7)
        elif key in [curses.KEY_ENTER, 10, 13]:  # Enter key
            selected_date = self.get_selected_date()
            self.last_viewed_date = selected_date
            if selected_date in self.tasks:
                # Create day view with callback for adding tasks
                def add_task_on_date(date):
                    self.last_viewed_date = date
                    self.return_to_day_view = True
                    return False, date

                self.day_view = DayView(selected_date, self.tasks[selected_date], add_task_callback=add_task_on_date)
                return True, None
            return False, selected_date
        elif key == ord('q'):  # Quit
            return False, None
        return True, None

    def add_task(self, task: Task):
        """Add a task to the calendar"""
        task_date = task.date.date()  # Extract date part from datetime
        if task_date not in self.tasks:
            self.tasks[task_date] = []
        self.tasks[task_date].append(task)
        # Sort tasks by time
        self.tasks[task_date].sort(key=lambda t: (t.time or datetime.time(23, 59)))
        
        # If we should return to day view, create it and return True to indicate we want to stay in expanded view
        if self.return_to_day_view and self.last_viewed_date:
            def add_task_on_date(date):
                self.last_viewed_date = date
                self.return_to_day_view = True
                return False, date
                
            self.day_view = DayView(task_date, self.tasks[task_date], add_task_callback=add_task_on_date)
            self.return_to_day_view = False
            return True  # Signal to stay in expanded view
        return False


    def get_selected_date(self) -> datetime.date:
        """Get the currently selected date"""
        return datetime.date(self.today.year, self.today.month, self.selected_day)
