from textual.widgets import Static
from textual.containers import Horizontal
from textual.message import Message
from textual.app import ComposeResult
from textual import on
from textual.events import Click

class Task(Static):
    class Updated(Message):
        def __init__(self, task_id: int) -> None:
            self.task_id = task_id
            super().__init__()
    
    class Deleted(Message):
        def __init__(self, task_id: int) -> None:
            self.task_id = task_id
            super().__init__()
    
    def __init__(self, task_data: dict) -> None:
        super().__init__("", classes="task-item")
        self.task_data = task_data
        self.task_id = task_data['id']
        self.can_focus = True
        self.completed = task_data.get('completed', False)
        self.in_progress = task_data.get('in_progress', False)
        
        if self.completed:
            self.add_class("completed-task")
        if self.in_progress:
            self.add_class("in-progress")
    
    def compose(self) -> ComposeResult:
        with Horizontal(classes="task-container"):
            display_text = f"{self.task_data['title']} @ {self.task_data['due_time']}"
            if self.task_data['description']:
                display_text += f" | {self.task_data['description']}"
        
            yield Static(display_text, classes="task-text")
            with Horizontal(classes="status-group"):
                yield Static("✓", classes="status-indicator complete-indicator") 
                yield Static("→", classes="status-indicator progress-indicator") 

    @on(Click)
    async def on_click(self, event: Click) -> None:
        # Replace entire click handler
        if "complete-indicator" in event.widget.classes:
            self.completed = not self.completed
            self.in_progress = False
            self.update_task_status()
            self.refresh_style()
        elif "progress-indicator" in event.widget.classes:
            self.in_progress = not self.in_progress 
            self.completed = False
            self.update_task_status()
            self.refresh_style()
        else:
            from .calendar import TaskEditForm
            task_form = TaskEditForm(self.task_data)
            result = await self.app.push_screen(task_form)
            if result is None:
                self.post_message(self.Deleted(self.task_id))
            elif result:
                self.post_message(self.Updated(self.task_id))
            self.refresh_all_views() 

    def toggle_complete(self) -> None:
        task_text = self.query_one(".task-text")
        complete_indicator = self.query_one(".complete-indicator")
        progress_indicator = self.query_one(".progress-indicator")

        # Toggle "completed" state
        if self.completed:
            self.completed = False
            task_text.remove_class("completed")
            self.remove_class("completed-task")
            complete_indicator.update("[ ]")
        else:
            self.completed = True
            self.in_progress = False  # Ensure "in_progress" is turned off
            task_text.add_class("completed")
            self.add_class("completed-task")
            complete_indicator.update("✓")
            progress_indicator.update("[-]")  # Reset progress indicator
            self.remove_class("in-progress")

            # Update database and UI
            self.update_task_status()
            self.post_message(self.Updated(self.task_id))

    def toggle_progress(self) -> None:
        progress_indicator = self.query_one(".progress-indicator")
        complete_indicator = self.query_one(".complete-indicator")
        task_text = self.query_one(".task-text")

        # Toggle "in_progress" state
        if self.in_progress:
            self.in_progress = False
            self.remove_class("in-progress")
            progress_indicator.update("[-]")
        else:
            self.in_progress = True
            self.completed = False  # Ensure "completed" is turned off
            self.add_class("in-progress")
            progress_indicator.update("→")
            task_text.remove_class("completed")
            self.remove_class("completed-task")
            complete_indicator.update("[ ]")  # Reset complete indicator

        # Update database and UI
        self.update_task_status()
        self.post_message(self.Updated(self.task_id))

    def update_task_status(self) -> None:
        """Update the task's status in the database."""
        self.app.db.update_task(self.task_id, completed=self.completed, in_progress=self.in_progress)

 
    
    def refresh_all_views(self) -> None:
        try:
            from .calendar import DayView
            day_view = self.app.screen.query_one(DayView)
            if day_view:
                day_view.refresh_tasks()
        except Exception:
            pass
        try:
            from .welcome import TodayContent
            today_content = self.app.screen.query_one(TodayContent)
            if today_content:
                today_content.refresh_tasks()
        except Exception:
            pass

    def refresh_style(self) -> None:
        if self.completed:
            self.add_class("completed-task")
            self.query_one(".task-text").add_class("completed")
            self.remove_class("in-progress")  # Make sure we remove in-progress when completed
        elif self.in_progress:  # Use elif to ensure they're mutually exclusive
            self.add_class("in-progress")
            self.remove_class("completed-task")
            self.query_one(".task-text").remove_class("completed")
        else:
            self.remove_class("completed-task")
            self.remove_class("in-progress")
            self.query_one(".task-text").remove_class("completed")
