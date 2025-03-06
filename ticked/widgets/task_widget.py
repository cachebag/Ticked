from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.events import Click
from textual.message import Message
from textual.widgets import Static

from ..utils.time_utils import convert_to_12hour


class Task(Static):
    BINDINGS = [
        Binding("c", "toggle_complete", "Complete"),
        Binding("p", "toggle_progress", "Progress"),
    ]

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
        self.task_id = task_data["id"]
        self.can_focus = True
        self.completed = task_data.get("completed", False)
        self.in_progress = task_data.get("in_progress", False)

        start_time = convert_to_12hour(task_data["start_time"])
        end_time = convert_to_12hour(task_data["end_time"])

        tooltip_text = (
            f"Title: {task_data['title']}\n"
            f"Time: {start_time} - {end_time}\n"
            f"Date: {task_data['due_date']}\n"
            f"Description: {task_data.get('description', 'No description')}"
        )

        self.tooltip = tooltip_text
        TOOLTIP_DELAY = 0.1

        if self.completed:
            self.add_class("completed-task")
        if self.in_progress:
            self.add_class("in-progress")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="task-container"):
            start_time = convert_to_12hour(self.task_data["start_time"])
            end_time = convert_to_12hour(self.task_data["end_time"])

            if start_time == "12:00 AM" and end_time == "11:59 PM":
                display_text = f"All Day | {self.task_data['title']}"
            else:
                display_text = f"{start_time} - {end_time} | {self.task_data['title']}"

            yield Static(display_text, classes="task-text")

            with Horizontal(classes="status-group"):
                yield Static("✓", classes="status-indicator complete-indicator")
                yield Static("→", classes="status-indicator progress-indicator")

    @on(Click)
    async def on_click(self, event: Click) -> None:
        if "complete-indicator" in event.widget.classes:
            await self.action_toggle_complete()
        elif "progress-indicator" in event.widget.classes:
            await self.action_toggle_progress()
        else:
            await self.action_edit_task()

    async def action_toggle_complete(self) -> None:
        if self.completed:
            self.completed = False
            self.remove_class("completed-task")
            self.query_one(".task-text").remove_class("completed")
            self.query_one(".complete-indicator").add_class("unchecked")
            self.query_one(".progress-indicator").add_class("in-progress")
        else:
            self.completed = True
            self.in_progress = False
            self.add_class("completed-task")
            self.remove_class("in-progress")
            self.query_one(".task-text").add_class("completed")
            self.query_one(".complete-indicator").remove_class("unchecked")
            self.query_one(".progress-indicator").remove_class("in-progress")

        self.update_task_status()
        self.post_message(self.Updated(self.task_id))
        self.focus()

    async def action_toggle_progress(self) -> None:
        if self.in_progress:
            self.in_progress = False
            self.remove_class("in-progress")
            self.query_one(".progress-indicator").remove_class("active")
        else:
            self.in_progress = True
            self.completed = False
            self.add_class("in-progress")
            self.remove_class("completed-task")
            self.query_one(".progress-indicator").add_class("active")
            self.query_one(".complete-indicator").remove_class("active")

        self.update_task_status()
        self.post_message(self.Updated(self.task_id))
        self.focus()

    async def action_edit_task(self) -> None:
        from ..ui.views.calendar import TaskEditForm

        task_form = TaskEditForm(self.task_data)
        result = await self.app.push_screen(task_form)

        if result is None:
            self.post_message(self.Deleted(self.task_id))
        elif result:
            self.task_data = result
            self.task_id = result["id"]

            start_time = convert_to_12hour(result["start_time"])
            end_time = convert_to_12hour(result["end_time"])
            display_text = f"{start_time} - {end_time} | {result['title']}"
            self.query_one(".task-text").update(display_text)

            self.tooltip = (
                f"Title: {result['title']}\n"
                f"Time: {start_time} - {end_time}\n"
                f"Date: {result['due_date']}\n"
                f"Description: {result.get('description', 'No description')}"
            )

            self.post_message(self.Updated(self.task_id))

    def toggle_complete(self) -> None:
        task_text = self.query_one(".task-text")
        complete_indicator = self.query_one(".complete-indicator", Static)
        progress_indicator = self.query_one(".progress-indicator", Static)

        if self.completed:
            self.completed = False
            task_text.remove_class("completed")
            self.remove_class("completed-task")
            complete_indicator.renderable = "unchecked"
            progress_indicator.renderable = "in-progress"
        else:
            self.completed = True
            self.in_progress = False
            task_text.add_class("completed")
            self.add_class("completed-task")
            self.remove_class("in-progress")
            complete_indicator.renderable = "✓"
            progress_indicator.renderable = "in-progress"

        self.update_task_status()
        self.post_message(self.Updated(self.task_id))
        self.focus()

    def toggle_progress(self) -> None:
        progress_indicator = self.query_one(".progress-indicator", Static)
        complete_indicator = self.query_one(".complete-indicator", Static)
        task_text = self.query_one(".task-text")

        if self.in_progress:
            self.in_progress = False
            self.remove_class("in-progress")
            progress_indicator.renderable = "[-]"
            complete_indicator.renderable = "[ ]"
        else:
            self.in_progress = True
            self.completed = False
            self.add_class("in-progress")
            self.remove_class("completed-task")
            task_text.remove_class("completed")
            progress_indicator.renderable = "→"
            complete_indicator.renderable = "[ ]"

        self.update_task_status()
        self.post_message(self.Updated(self.task_id))
        self.focus()

    def update_task_status(self) -> None:
        self.app.db.update_task(
            self.task_id, completed=self.completed, in_progress=self.in_progress
        )

    def refresh_all_views(self) -> None:
        try:
            from ..ui.views.calendar import DayView

            day_view = self.app.screen.query_one(DayView)
            if day_view:
                day_view.refresh_tasks()
        except Exception:
            pass
        try:
            from ..ui.views.welcome import TodayContent

            today_content = self.app.screen.query_one(TodayContent)
            if today_content:
                today_content.refresh_tasks()
        except Exception:
            pass

    def refresh_style(self) -> None:
        if self.completed:
            self.add_class("completed-task")
            self.query_one(".task-text").add_class("completed")
            self.remove_class("in-progress")
        elif self.in_progress:
            self.add_class("in-progress")
            self.remove_class("completed-task")
            self.query_one(".task-text").remove_class("completed")
        else:
            self.remove_class("completed-task")
            self.remove_class("in-progress")
            self.query_one(".task-text").remove_class("completed")
