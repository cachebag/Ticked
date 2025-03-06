import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Markdown, Static, TextArea

from ticked.widgets.task_widget import Task


class TabButton(Button):
    def __init__(self, label: str, tab_id: str):
        super().__init__(label, id=f"tab_{tab_id}")
        self.tab_id = tab_id
        self.add_class("tab-button")

    def toggle_active(self, is_active: bool):
        if is_active:
            self.add_class("active")
        else:
            self.remove_class("active")


class ASCIIAnimation(Static):
    DEFAULT_CSS = """
    ASCIIAnimation {
        height: 100%;
        content-align: center middle;
        text-align: center;
    }
    """

    def __init__(self):
        super().__init__("")
        self.current_frame = 0
        self.frames = [
            ".",
            "|",
            "/",
        ]

    async def on_mount(self) -> None:
        self.update_animation()

    def update_animation(self) -> None:
        self.update(self.frames[self.current_frame])
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        self.set_timer(0.5, self.update_animation)


class DashboardCard(Container):
    def __init__(self, title: str, content: str = "", classes: str = None) -> None:
        super().__init__(classes=classes)
        self.title = title
        self.content = content
        self.add_class("dashboard-card")

    def compose(self) -> ComposeResult:
        yield Static(self.title, classes="card-title")
        yield Static(self.content, classes="card-content")


class NowPlayingCard(Container):
    DEFAULT_CSS = """
    NowPlayingCard {
        width: 100%;
        height: 100%;
        padding: 1;
        border-bottom: tall $primary;
        border: $accent;
    }
    
    .now-playing-title {
        text-align: center;
        margin-bottom: 1;
    }
    
    .track-info {
        text-align: center;
        margin-bottom: 1;
    }
    
    .track-controls {
        layout: horizontal;
        align: center middle;
        width: 100%;
    }
    
    .control-btn {
        width: 3;
        min-width: 3;
        height: 3;
        margin: 0 1;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Now Playing", classes="card-title")
        yield Static(
            "No track playing - Make sure you authenticate in the Spotify page",
            id="track-name",
            classes="track-info",
        )
        yield Static("", id="artist-name", classes="track-info")
        with Horizontal(classes="track-controls"):
            yield Button("⏮", id="prev-btn", classes="control-btn")
            yield Button("⏯", id="play-pause-btn", classes="control-btn")
            yield Button("⏭", id="next-btn", classes="control-btn")

    def update_track(self, track_name: str, artist_name: str) -> None:
        self.query_one("#track-name").update(track_name)
        self.query_one("#artist-name").update(artist_name)

    async def on_mount(self) -> None:
        self.set_interval(3, self.poll_spotify_now_playing)

    def poll_spotify_now_playing(self) -> None:
        spotify_client = self.app.get_spotify_client()
        if not spotify_client:
            self.update_track(
                "No track playing - Make sure you authenticate in the Spotify page", ""
            )
            return

        try:
            playback = spotify_client.current_playback()
            if playback and playback.get("item"):
                track_name = playback["item"]["name"]
                artist_name = ", ".join(a["name"] for a in playback["item"]["artists"])
                self.update_track(track_name, artist_name)
            else:
                self.update_track(
                    "No track playing - Make sure you authenticate in the Spotify page",
                    "",
                )
        except Exception as e:
            print(f"Error fetching Spotify playback: {e}")
            self.update_track(
                "No track playing - Make sure you authenticate in the Spotify page", ""
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        spotify_client = self.app.get_spotify_client()
        if not spotify_client:
            self.notify("No Spotify connection", severity="error")
            return

        try:
            if event.button.id == "play-pause-btn":
                event.stop()
                current_playback = spotify_client.current_playback()
                if current_playback and current_playback["is_playing"]:
                    spotify_client.pause_playback()
                else:
                    spotify_client.start_playback()
                self.poll_spotify_now_playing()
            elif event.button.id == "prev-btn":
                event.stop()
                spotify_client.previous_track()
                self.poll_spotify_now_playing()
                playback = spotify_client.current_playback()
                if playback and playback.get("item"):
                    track_name = playback["item"]["name"]
                    artist_name = ", ".join(
                        a["name"] for a in playback["item"]["artists"]
                    )
                    self.notify(f"Now playing: {track_name} by {artist_name}")
            elif event.button.id == "next-btn":
                event.stop()
                spotify_client.next_track()
                self.poll_spotify_now_playing()
                playback = spotify_client.current_playback()
                if playback and playback.get("item"):
                    track_name = playback["item"]["name"]
                    artist_name = ", ".join(
                        a["name"] for a in playback["item"]["artists"]
                    )
                    self.notify(f"Now playing: {track_name} by {artist_name}")
        except Exception as e:
            self.notify(f"Playback error: {str(e)}", severity="error")


class NotesCard(Container):
    """Card to display the current day's notes."""

    def __init__(self) -> None:
        super().__init__()
        self.notes_content = "# Today's Notes\nStart writing your notes here..."

    def compose(self) -> ComposeResult:
        yield Static("Today's Notes", classes="card-title")
        yield Markdown("", id="daily-notes-content", classes="markdown-content")

    def on_mount(self) -> None:
        today_date = datetime.now().strftime("%Y-%m-%d")
        notes = self.app.db.get_notes(today_date)

        if notes:
            self.notes_content = notes
        else:
            self.notes_content = "# Today's Notes\nStart writing your notes here..."

        self.query_one("#daily-notes-content").update(self.notes_content)
        self.call_later(self._apply_markdown_classes)

    def _apply_markdown_classes(self) -> None:
        """Apply the proper CSS classes to markdown elements after rendering."""
        try:
            viewer = self.query_one("#daily-notes-content")

            for i in range(1, 7):
                for heading in viewer.query(f"Heading{i}"):
                    heading.add_class(f"markdown--h{i}")

            for ul in viewer.query("UnorderedList"):
                ul.add_class("markdown--list")

            for ol in viewer.query("OrderedList"):
                ol.add_class("markdown--list")

            for code in viewer.query("CodeBlock"):
                code.add_class("markdown--code")

            for blockquote in viewer.query("BlockQuote"):
                blockquote.add_class("markdown--blockquote")

            for link in viewer.query("Link"):
                link.add_class("markdown--link")

            for table in viewer.query("Table"):
                table.add_class("markdown--table")

            for th in viewer.query("TableHeader"):
                th.add_class("markdown--th")

            for td in viewer.query("TableCell"):
                td.add_class("markdown--td")

        except Exception as e:
            print(f"Error applying markdown classes: {e}")

    def refresh_notes(self) -> None:
        today_date = datetime.now().strftime("%Y-%m-%d")
        notes = self.app.db.get_notes(today_date)

        if notes:
            self.notes_content = notes
        else:
            self.notes_content = "# Today's Notes\nStart writing your notes here..."

        viewer = self.query_one("#daily-notes-content")
        viewer.update(self.notes_content)
        self.call_later(self._apply_markdown_classes)


class TodayContent(Container):

    def __init__(self) -> None:
        super().__init__()
        self.tasks_to_mount = None
        self.package_dir = Path(__file__).parent.parent.parent

    def compose(self) -> ComposeResult:
        with Grid(classes="dashboard-grid"):
            with Vertical():
                with Container(classes="tasks-card"):
                    with DashboardCard("Today's Tasks"):
                        with Vertical(id="today-tasks-list", classes="tasks-list"):
                            yield Static(
                                "No Tasks - Head over to your calendar to add some!",
                                classes="empty-schedule",
                            )

                # Add notes card below the tasks card
                with Container(classes="notes-card"):
                    yield NotesCard()

            with Container(classes="right-column"):
                with Grid(classes="right-top-grid"):
                    quote = self.get_cached_quote()
                    yield DashboardCard("Quote of the Day", quote)
                    yield NowPlayingCard()

                with Container(classes="bottom-card"):
                    yield UpcomingTasksView()

    def on_mount(self) -> None:
        if self.tasks_to_mount is not None:
            self._do_mount_tasks(self.tasks_to_mount)
            self.tasks_to_mount = None

    def on_task_updated(self, event: Task.Updated) -> None:
        self.refresh_tasks()
        event.prevent_default()

    def on_task_deleted(self, event: Task.Deleted) -> None:
        self.refresh_tasks()
        event.prevent_default()

    def mount_tasks(self, tasks):
        if self.is_mounted:
            self._do_mount_tasks(tasks)
        else:
            self.tasks_to_mount = tasks

    def _do_mount_tasks(self, tasks):
        tasks_list = self.query_one("#today-tasks-list")
        current_focused_task_id = None

        focused = self.app.focused
        if isinstance(focused, Task):
            current_focused_task_id = focused.task_id

        tasks_list.remove_children()

        if tasks:
            for task in tasks:
                task_widget = Task(task)
                tasks_list.mount(task_widget)
                if current_focused_task_id and task["id"] == current_focused_task_id:
                    task_widget.focus()
        else:
            tasks_list.mount(
                Static(
                    "No tasks - Head to your calendar to add some!",
                    classes="empty-schedule",
                )
            )

    def refresh_tasks(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = self.app.db.get_tasks_for_date(today)
        self._do_mount_tasks(tasks)

        upcoming_view = self.query_one(UpcomingTasksView)
        if upcoming_view:
            upcoming_view.refresh_tasks()

        # Also refresh the notes when refreshing tasks
        notes_card = self.query_one(NotesCard)
        if notes_card:
            notes_card.refresh_notes()

        self.refresh()

    def get_cached_quote(self):
        quotes_file = self.package_dir / "quotes_cache.json"
        try:
            with open(quotes_file, "r") as file:
                quotes = json.load(file)
                random_quote = random.choice(quotes)
                return f"{random_quote['q']} \n\n — {random_quote['a']}"
        except FileNotFoundError:
            self.fetch_and_cache_quotes()
            return "No quotes available. Please try again later."

    def fetch_and_cache_quotes(self):
        try:
            response = requests.get("https://zenquotes.io/api/quotes", timeout=10)
            if response.status_code == 200:
                quotes_data = response.json()
                quotes_file = self.package_dir / "quotes_cache.json"
                with open(quotes_file, "w") as file:
                    json.dump(quotes_data, file)
                print("Quotes cached successfully!")
            else:
                print(f"Failed to fetch quotes: {response.status_code}")
        except requests.RequestException as e:
            print(f"Error fetching quotes: {e}")

    def update_now_playing(self, track_name: str, artist_name: str) -> None:
        now_playing = self.query_one(NowPlayingCard)
        if now_playing:
            now_playing.update_track(track_name, artist_name)


class WelcomeMessage(Static):
    DEFAULT_CSS = """
    WelcomeMessage {
        width: 100%;
        height: auto;
        content-align: center middle;
        text-align: center;
        padding: 1;
    }
    """


class WelcomeContent(Container):
    DEFAULT_CSS = """
    WelcomeContent {
        width: 100%;
        height: 100%;
        align: center middle;
        padding: 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield WelcomeMessage("║       Welcome to TICK        ║")
        yield WelcomeMessage("")
        yield WelcomeMessage(
            "For detailed instructions, [yellow]reference the docs on our[/yellow] "
            "[@click='app.open_url(\"https://github.com/cachebag/Ticked\")']GitHub Repository[/]"
        )
        yield WelcomeMessage("")
        yield WelcomeMessage("Navigation:")
        yield WelcomeMessage("• Use [red]↑/↓ ←/→ [/red] arrows to navigate the program")
        yield WelcomeMessage("• Press [red]Enter[/red] to select an item")
        yield WelcomeMessage("• Press [red]Ctrl+Q[/red] to quit")
        yield WelcomeMessage("• Press [red]Esc[/red] to toggle the main menu options")
        yield WelcomeMessage("")
        yield WelcomeMessage(
            "Select an option from the menu to begin (you can use your mouse too, we don't judge.)"
        )


class WelcomeView(Container):

    BINDINGS = [
        Binding("left", "move_left", "Left", show=True),
        Binding("right", "move_right", "Right", show=True),
        Binding("enter", "select_tab", "Select", show=True),
        Binding("up", "move_up", "Up", show=True),
        Binding("down", "move_down", "Down", show=True),
        Binding("tab", "toggle_filter", "Toggle Upcoming Tasks", show=True),
    ]

    def __init__(self):
        super().__init__()
        self._focused_tasks = False

    def on_focus(self, event) -> None:
        if isinstance(event.widget, Task):
            tasks_list = self.query_one("#today-tasks-list")
            if event.widget in tasks_list.query(Task):
                self._focused_tasks = True

    def on_blur(self, event) -> None:
        if self._focused_tasks and isinstance(event.widget, Task):
            self._focused_tasks = False

    async def action_move_down(self) -> None:
        current = self.app.focused

        if isinstance(current, TabButton):
            tasks = list(self.query_one("#today-tasks-list").query(Task))
            if tasks:
                self._focused_tasks = True
                tasks[0].focus()
        elif isinstance(current, Task):
            tasks = list(self.query_one("#today-tasks-list").query(Task))
            if tasks:
                current_idx = tasks.index(current)
                if current_idx < len(tasks) - 1:  # Only navigate within tasks
                    next_idx = current_idx + 1
                    tasks[next_idx].focus()

    async def action_move_up(self) -> None:
        current = self.app.focused

        if isinstance(current, Task):
            tasks = list(self.query_one("#today-tasks-list").query(Task))
            if tasks:
                current_idx = tasks.index(current)
                if current_idx == 0:
                    self._focused_tasks = False
                    today_tab = self.query_one("TabButton#tab_today")
                    today_tab.focus()
                else:
                    prev_idx = current_idx - 1
                    tasks[prev_idx].focus()

    def compose(self) -> ComposeResult:
        with Horizontal(classes="tab-bar"):
            yield TabButton("Today", "today")
            yield TabButton("Welcome", "welcome")

        with Container(id="tab-content"):
            yield TodayContent()
            yield WelcomeContent()

    def on_mount(self) -> None:
        is_first_time = self.app.db.is_first_launch()

        today_tab = self.query_one("TabButton#tab_today")
        welcome_tab = self.query_one("TabButton#tab_welcome")
        welcome_content = self.query_one(WelcomeContent)
        today_content = self.query_one(
            TodayContent
        )  # Make sure to get the today_content

        if is_first_time:
            welcome_tab.toggle_active(True)
            welcome_tab.focus()

            welcome_content.styles.display = "block"
            today_content.styles.display = "none"

            self.app.db.mark_first_launch_complete()
        else:
            today_tab.toggle_active(True)
            today_tab.focus()

            welcome_content.styles.display = "none"
            today_content.styles.display = "block"

            today = datetime.now().strftime("%Y-%m-%d")
            tasks = self.app.db.get_tasks_for_date(today)
            today_content.mount_tasks(tasks)

    def get_initial_focus(self) -> Optional[Widget]:
        return self.query_one(TabButton, id="tab_today")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "hide_welcome":
            welcome_content = self.query_one(WelcomeContent)
            welcome_content.styles.display = "none"
            event.stop()
            return

        if not event.button.id.startswith("tab_"):
            return

        event.stop()

        tab_buttons = self.query(".tab-button")
        welcome_content = self.query_one(WelcomeContent)
        today_content = self.query_one(TodayContent)

        for button in tab_buttons:
            button.toggle_active(button.id == event.button.id)

        if event.button.id == "tab_welcome":
            welcome_content.styles.display = "block"
            today_content.styles.display = "none"
        elif event.button.id == "tab_today":
            welcome_content.styles.display = "none"
            today_content.styles.display = "block"

    async def action_move_left(self) -> None:
        if self._focused_tasks:
            return

        tabs = list(self.query(TabButton))
        current = self.app.focused
        if current in tabs:
            current_idx = tabs.index(current)
            prev_idx = (current_idx - 1) % len(tabs)
            tabs[prev_idx].focus()

    async def action_move_right(self) -> None:
        if self._focused_tasks:
            return

        tabs = list(self.query(TabButton))
        current = self.app.focused
        if current in tabs:
            current_idx = tabs.index(current)
            next_idx = (current_idx + 1) % len(tabs)
            tabs[next_idx].focus()

    async def action_select_tab(self) -> None:
        current = self.app.focused
        if isinstance(current, TabButton):
            self.app.focused.press()
        elif isinstance(current, Task):
            await current.action_edit_task()

    async def action_toggle_filter(self) -> None:
        upcoming = self.query_one(UpcomingTasksView)
        if upcoming.filter_days == 7:
            upcoming.filter_days = 30
            for btn in upcoming.query(".filter-btn"):
                btn.remove_class("active")
            thirty_day_btn = upcoming.query_one("#filter-30")
            thirty_day_btn.add_class("active")
        else:
            upcoming.filter_days = 7
            for btn in upcoming.query(".filter-btn"):
                btn.remove_class("active")
            seven_day_btn = upcoming.query_one("#filter-7")
            seven_day_btn.add_class("active")

        upcoming.refresh_tasks()


class UpcomingTasksView(Container):

    def __init__(self):
        super().__init__()
        self.filter_days = 7

    def compose(self) -> ComposeResult:
        with Horizontal(classes="header-row"):
            yield Static("Upcoming Tasks", classes="card-title")
            yield Static("", classes="header-spacer")
            with Horizontal(classes="filter-buttons"):
                yield Button("7d", id="filter-7", classes="filter-btn active")
                yield Button("30d", id="filter-30", classes="filter-btn")

        with Vertical(id="upcoming-tasks-list", classes="tasks-list"):
            yield Static("Loading...", classes="empty-schedule-up")

    def on_mount(self) -> None:
        self.refresh_tasks()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id.startswith("filter-"):
            days = int(event.button.id.split("-")[1])
            self.filter_days = days

            for btn in self.query(".filter-btn"):
                btn.remove_class("active")
            event.button.add_class("active")
            event.stop()

            self.refresh_tasks()

    def refresh_tasks(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = self.app.db.get_upcoming_tasks(today, self.filter_days)

        tasks_list = self.query_one("#upcoming-tasks-list")
        tasks_list.remove_children()

        if tasks:
            for task in tasks:
                task_with_date = task.copy()
                date_obj = datetime.strptime(task["due_date"], "%Y-%m-%d")
                date_str = date_obj.strftime("%B %d, %Y")

                if task["description"]:
                    task_with_date["display_text"] = (
                        f"{task['title']} @ {task['start_time']} | {task['description']} | On {date_str}"
                    )
                else:
                    task_with_date["display_text"] = (
                        f"{task['title']} @ {task['start_time']} | On {date_str}"
                    )

                task_widget = Task(task_with_date)
                tasks_list.mount(task_widget)
        else:
            tasks_list.mount(
                Static(
                    "No tasks - Head to your calendar to add some!",
                    classes="empty-schedule",
                )
            )
