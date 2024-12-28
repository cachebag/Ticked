from textual.widgets import Static
from textual.message import Message

class Task(Static):
    class Updated(Message):
        """Emitted when a task is updated"""
        def __init__(self, task_id: int) -> None:
            self.task_id = task_id
            super().__init__()

    class Deleted(Message):
        """Emitted when a task is deleted"""
        def __init__(self, task_id: int) -> None:
            self.task_id = task_id
            super().__init__()

    def __init__(self, task_data: dict) -> None:
        self.task_data = task_data
        display_text = f"{task_data['title']} @ {task_data['due_time']}"
        if task_data['description']:
            display_text += f" | {task_data['description']}"
        super().__init__(display_text, classes="task-item")
        self.task_id = task_data['id']
        self.can_focus = True

    async def on_click(self) -> None:
        from .calendar import TaskEditForm
        
        task_form = TaskEditForm(self.task_data)
        updated_task = await self.app.push_screen(task_form)
        
        if updated_task is None:  
            self.post_message(self.Deleted(self.task_id))
            self.refresh_all_views()
        elif updated_task:  
            self.post_message(self.Updated(self.task_id))
            self.refresh_all_views()


    def refresh_all_views(self) -> None:
        """Refresh all possible views that might display tasks."""
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
