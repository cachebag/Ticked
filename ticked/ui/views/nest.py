import os
import re
import shutil
import time
from difflib import SequenceMatcher
from typing import Optional

from jedi import Script
from rich.markup import escape
from rich.syntax import Syntax
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.events import Key, MouseDown
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button,
    DataTable,
    DirectoryTree,
    Input,
    Label,
    Static,
    TextArea,
)

from ...ui.mixins.focus_mixin import InitialFocusMixin


class EditorTab:
    def __init__(self, path: str, content: str):
        self.path = path
        self.content = content
        self.modified = False
        # Per-buffer undo/redo stacks
        self.undo_stack = []
        self.redo_stack = []
        # Cursor and scroll position for this buffer
        self.cursor_position = (0, 0)
        self.scroll_position = (0, 0)


class FileCreated(Message):
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path


class FolderCreated(Message):
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path


class FileDeleted(Message):
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path


class FilterableDirectoryTree(DirectoryTree):
    def __init__(self, path: str, show_hidden: bool = False, **kwargs) -> None:
        super().__init__(path, **kwargs)
        self.show_hidden = show_hidden

    def filter_paths(self, paths: list[str]) -> list[str]:
        if self.show_hidden:
            return paths
        return [path for path in paths if not os.path.basename(path).startswith(".")]

    def _get_expanded_paths(self) -> list[str]:
        """Get a list of all expanded directory paths."""
        expanded_paths = []

        def collect_expanded(node):
            if node.is_expanded and hasattr(node.data, "path"):
                expanded_paths.append(node.data.path)
            for child in node.children:
                if child.children:
                    collect_expanded(child)

        if self.root:
            collect_expanded(self.root)

        return expanded_paths

    def _restore_expanded_paths(self, paths: list[str]) -> None:
        """Restore previously expanded directories."""
        for path in paths:
            try:
                self.select_path(path)
                if self.cursor_node and not self.cursor_node.is_expanded:
                    self.toggle_node(self.cursor_node)
            except Exception:
                pass

    def refresh_tree(self) -> None:
        """Refresh the tree while maintaining expanded directories."""
        expanded_paths = self._get_expanded_paths()
        cursor_path = self.cursor_node.data.path if self.cursor_node else None

        self.path = self.path
        self.reload()

        self._restore_expanded_paths(expanded_paths)

        if cursor_path:
            try:
                self.select_path(cursor_path)
            except Exception:
                pass

        self.refresh(layout=True)

    async def action_delete_selected(self) -> None:
        if self.cursor_node is None:
            self.app.notify("No file or folder selected", severity="warning")
            return

        path = self.cursor_node.data.path
        dialog = DeleteConfirmationDialog(path)
        await self.app.push_screen(dialog)
        if hasattr(self.app, "main_tree") and self.app.main_tree:
            self.app.main_tree.refresh_tree()

    def on_key(self, event: Key) -> None:
        if event.key == "d":
            self.run_worker(self.action_delete_selected())
            event.prevent_default()
            event.stop()
        elif event.key == "?" and event.shift:
            if self.cursor_node:
                path = self.cursor_node.data.path
                is_dir = os.path.isdir(path)
                menu_items = [
                    ("Rename", "rename"),
                    ("Delete", "delete"),
                ]
                if is_dir:
                    menu_items += [
                        ("New File", "new_file"),
                        ("New Folder", "new_folder"),
                        ("Copy", "copy"),
                        ("Cut", "cut"),
                    ]
                else:
                    menu_items += [
                        ("Copy", "copy"),
                        ("Cut", "cut"),
                    ]
                # Position the menu near the currently selected node when triggered via keyboard
                tree_region = self.region
                
                # Try to position near the selected node if possible
                try:
                    if hasattr(self.cursor_node, 'line') and self.cursor_node.line >= 0:
                        # Calculate approximate position of the selected node
                        node_y = tree_region.y + (self.cursor_node.line * 2) + 20  # Rough estimate
                        menu_x = tree_region.x + tree_region.width - 160  # Right side of tree
                        menu_y = max(tree_region.y + 20, min(node_y, tree_region.y + tree_region.height - 200))
                    else:
                        # Fallback to a position near the start of the tree
                        menu_x = tree_region.x + tree_region.width - 160
                        menu_y = tree_region.y + 50
                except Exception:
                    # Final fallback
                    menu_x = tree_region.x + tree_region.width - 160
                    menu_y = tree_region.y + 50
                
                menu = ContextMenu(menu_items, menu_x, menu_y, path)
                self.app.push_screen(menu)
            event.prevent_default()
            event.stop()

    def on_mouse_down(self, event: MouseDown) -> None:
        if event.button == 3:
            try:
                offset = event.offset
                node = self.get_node_at_line(
                    offset.y - 1
                )  # offset might come with padding so we -1 to get the actual line

                if node is not None:
                    self.select_node(node)

                    path = node.data.path
                    is_dir = os.path.isdir(path)

                    menu_items = [
                        ("Rename", "rename"),
                        ("Delete", "delete"),
                    ]

                    if is_dir:
                        menu_items += [
                            ("New File", "new_file"),
                            ("New Folder", "new_folder"),
                            ("Copy", "copy"),
                            ("Cut", "cut"),
                        ]
                    else:
                        menu_items += [
                            ("Copy", "copy"),
                            ("Cut", "cut"),
                        ]

                    menu = ContextMenu(menu_items, event.screen_x, event.screen_y, path)
                    self.app.push_screen(menu)

                event.stop()
            except Exception as e:
                self.app.notify(f"Context menu error: {str(e)}", severity="error")


class NewFileDialog(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("f1", "submit", "Submit"),
        Binding("tab", "next_field", "Next Field"),
        Binding("shift+tab", "previous_field", "Previous Field"),
        Binding("up", "move_up", "Move Up"),
        Binding("down", "move_down", "Move Down"),
    ]

    def __init__(self, initial_path: str) -> None:
        super().__init__()
        self.selected_path = initial_path

    def compose(self) -> ComposeResult:
        with Container(classes="file-form-container"):
            with Vertical(classes="file-form"):
                yield Static("Create New File", classes="file-form-header")

                with Vertical():
                    yield Label("Selected Directory:", classes="selected-path-label")
                    yield Static(str(self.selected_path), id="selected-path")

                with Vertical():
                    yield Label("Filename")
                    yield Input(placeholder="Enter filename", id="filename")

                yield FilterableDirectoryTree(os.path.expanduser("~"))

                with Horizontal(classes="form-buttons"):
                    yield Button("Cancel", variant="error", id="cancel")
                    yield Button("Create File", variant="success", id="submit")

    def on_mount(self) -> None:
        self.query_one("#filename").focus()

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self.selected_path = event.path
        self.query_one("#selected-path").update(str(self.selected_path))

    def on_input_submitted(self) -> None:
        self.action_submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "submit":
            self._handle_submit()

    def _handle_submit(self) -> None:
        filename = self.query_one("#filename").value
        if not filename:
            self.notify("Filename is required", severity="error")
            return

        full_path = os.path.join(self.selected_path, filename)

        if os.path.exists(full_path):
            self.notify("File already exists!", severity="error")
            return

        try:
            with open(full_path, "w") as f:
                f.write("")
            self.dismiss(full_path)
            self.app.post_message(FileCreated(full_path))
            if hasattr(self.app, "main_tree") and self.app.main_tree:
                self.app.main_tree.refresh_tree()

            editor = self.app.query_one(CodeEditor)
            editor.open_file(full_path)
            editor.focus()
            self.dismiss(full_path)
        except Exception as e:
            self.notify(f"Error creating file: {str(e)}", severity="error")
            self.dismiss(None)

    async def action_cancel(self) -> None:
        self.dismiss(None)

    async def action_submit(self) -> None:
        self._handle_submit()

    async def action_next_field(self) -> None:
        current = self.app.focused
        if isinstance(current, Input):
            self.query_one(FilterableDirectoryTree).focus()
        elif isinstance(current, FilterableDirectoryTree):
            self.query_one("#submit").focus()
        elif isinstance(current, Button):
            self.query_one("#filename").focus()
        else:
            self.query_one("#filename").focus()

    async def action_previous_field(self) -> None:
        current = self.app.focused
        if isinstance(current, Input):
            self.query_one("#submit").focus()
        elif isinstance(current, FilterableDirectoryTree):
            self.query_one("#filename").focus()
        elif isinstance(current, Button):
            self.query_one(FilterableDirectoryTree).focus()
        else:
            self.query_one("#filename").focus()

    async def action_move_up(self) -> None:
        current = self.app.focused
        if isinstance(current, Button):
            self.query_one(FilterableDirectoryTree).focus()
        elif isinstance(current, Input):
            self.query_one("#submit").focus()

    async def action_move_down(self) -> None:
        current = self.app.focused
        if isinstance(current, Button):
            self.query_one("#filename").focus()
        elif isinstance(current, Input):
            self.query_one(FilterableDirectoryTree).focus()


class NewFolderDialog(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("f1", "submit", "Submit"),
        Binding("tab", "next_field", "Next Field"),
        Binding("shift+tab", "previous_field", "Previous Field"),
        Binding("up", "move_up", "Move Up"),
        Binding("down", "move_down", "Move Down"),
    ]

    def __init__(self, initial_path: str) -> None:
        super().__init__()
        self.selected_path = initial_path

    def compose(self) -> ComposeResult:
        with Container(classes="file-form-container"):
            with Vertical(classes="file-form"):
                yield Static("Create New Folder", classes="file-form-header")

                with Vertical():
                    yield Label("Selected Directory:", classes="selected-path-label")
                    yield Static(str(self.selected_path), id="selected-path")

                with Vertical():
                    yield Label("Folder Name")
                    yield Input(placeholder="Enter folder name", id="foldername")

                yield FilterableDirectoryTree(os.path.expanduser("~"))

                with Horizontal(classes="form-buttons"):
                    yield Button("Cancel", variant="error", id="cancel")
                    yield Button("Create Folder", variant="success", id="submit")

    def on_mount(self) -> None:
        self.query_one("#foldername").focus()

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self.selected_path = event.path
        self.query_one("#selected-path").update(str(self.selected_path))

    def on_input_submitted(self) -> None:
        self.action_submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "submit":
            self._handle_submit()

    def _handle_submit(self) -> None:
        foldername = self.query_one("#foldername").value
        if not foldername:
            self.notify("Folder name is required", severity="error")
            return

        full_path = os.path.join(self.selected_path, foldername)

        if os.path.exists(full_path):
            self.notify("Folder already exists!", severity="error")
            return

        try:
            os.makedirs(full_path)
            self.dismiss(full_path)
            self.app.post_message(FolderCreated(full_path))
            if hasattr(self.app, "main_tree") and self.app.main_tree:
                self.app.main_tree.refresh_tree()
            self.dismiss(full_path)
        except Exception as e:
            self.notify(f"Error creating folder: {str(e)}", severity="error")
            self.dismiss(None)

    async def action_cancel(self) -> None:
        self.dismiss(None)

    async def action_submit(self) -> None:
        self._handle_submit()

    async def action_next_field(self) -> None:
        current = self.app.focused
        if isinstance(current, Input):
            self.query_one(FilterableDirectoryTree).focus()
        elif isinstance(current, FilterableDirectoryTree):
            self.query_one("#submit").focus()
        elif isinstance(current, Button):
            self.query_one("#foldername").focus()
        else:
            self.query_one("#foldername").focus()

    async def action_previous_field(self) -> None:
        current = self.app.focused
        if isinstance(current, Input):
            self.query_one("#submit").focus()
        elif isinstance(current, FilterableDirectoryTree):
            self.query_one("#foldername").focus()
        elif isinstance(current, Button):
            self.query_one(FilterableDirectoryTree).focus()
        else:
            self.query_one("#foldername").focus()

    async def action_move_up(self) -> None:
        current = self.app.focused
        if isinstance(current, Button):
            self.query_one(FilterableDirectoryTree).focus()
        elif isinstance(current, Input):
            self.query_one("#submit").focus()

    async def action_move_down(self) -> None:
        current = self.app.focused
        if isinstance(current, Button):
            self.query_one("#foldername").focus()
        elif isinstance(current, Input):
            self.query_one(FilterableDirectoryTree).focus()


class DeleteConfirmationDialog(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
        Binding("tab", "next_button", "Next Button"),
        Binding("shift+tab", "previous_button", "Previous Button"),
        Binding("left", "focus_cancel", "Focus Cancel"),
        Binding("right", "focus_confirm", "Focus Confirm"),
    ]

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path
        self.file_name = os.path.basename(path)
        self.is_directory = os.path.isdir(path)

    def compose(self) -> ComposeResult:
        with Container(classes="file-form-container-d"):
            with Vertical(classes="file-form"):
                item_type = "folder" if self.is_directory else "file"
                yield Static(f"Delete {item_type}", classes="file-form-header")
                yield Static(
                    f"Are you sure you want to delete this {item_type}?",
                    classes="delete-confirm-message",
                )
                yield Static(self.file_name, classes="delete-confirm-filename")

                with Horizontal(classes="form-buttons"):
                    yield Button("Cancel", variant="primary", id="cancel")
                    yield Button("Delete", variant="error", id="confirm")

    def on_mount(self) -> None:
        self.query_one("#cancel").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
        elif event.button.id == "confirm":
            self._handle_delete()

    def _handle_delete(self) -> None:
        path = self.path
        try:
            if os.path.isdir(path):
                self.app.notify(f"Deleting directory: {path}")
                shutil.rmtree(path)
            else:
                self.app.notify(f"Deleting file: {path}")
                os.unlink(path)

            self.app.post_message(FileDeleted(path))
            if hasattr(self.app, "main_tree") and self.app.main_tree:
                self.app.main_tree.refresh_tree()
                try:
                    parent_path = os.path.dirname(path)
                    if os.path.exists(parent_path):
                        self.app.main_tree.select_path(parent_path)
                except Exception:
                    pass

            self.app.notify(f"Deleted: {os.path.basename(path)}")
            self.dismiss(True)
        except Exception as e:
            self.app.notify(f"Error deleting: {str(e)}", severity="error")
            self.dismiss(False)

    async def action_cancel(self) -> None:
        self.dismiss(False)

    async def action_confirm(self) -> None:
        self._handle_delete()

    async def action_next_button(self) -> None:
        if self.app.focused == self.query_one("#cancel"):
            self.query_one("#confirm").focus()
        else:
            self.query_one("#cancel").focus()

    async def action_previous_button(self) -> None:
        if self.app.focused == self.query_one("#confirm"):
            self.query_one("#cancel").focus()
        else:
            self.query_one("#confirm").focus()

    async def action_focus_cancel(self) -> None:
        self.query_one("#cancel").focus()

    async def action_focus_confirm(self) -> None:
        self.query_one("#confirm").focus()


class StatusBar(Static):
    def __init__(self) -> None:
        super().__init__("", id="status-bar")
        self.mode = "NORMAL"
        self.file_info = ""
        self.command = ""
        self._update_content()

    def update_mode(self, mode: str) -> None:
        self.mode = mode.upper()
        self._update_content()

    def update_file_info(self, info: str) -> None:
        self.file_info = info
        self._update_content()

    def update_command(self, command: str) -> None:
        self.command = command
        self._update_content()

    def _update_content(self) -> None:
        mode_style = {
            "NORMAL": "bold blue", 
            "INSERT": "bold green", 
            "COMMAND": "bold magenta",
            "VISUAL": "bold cyan",
            "VISUAL LINE": "bold cyan"
        }
        color = mode_style.get(self.mode, "bold white")

        parts = [f"[{color}]{self.mode}[/]"]
        if self.file_info:
            parts.append(escape(self.file_info))
        if self.command:
            parts.append(f"[bold yellow]{escape(self.command)}[/]")

        text = Text.from_markup(" ".join(parts))

        self.update(text)


class AutoCompletePopup(DataTable):
    """Popup widget for displaying autocompletion suggestions."""

    class Selected(Message):
        """Message emitted when a completion is selected."""

        def __init__(self, value: str) -> None:
            self.value = value
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self.cursor_type = "row"
        self.add_column("Completion", width=30)
        self.add_column("Type", width=20)
        self.add_column("Info", width=40)
        self.styles.background = "rgb(30,30,30)"
        self.styles.width = 90
        self.styles.height = 10
        self.can_focus = True

        self.styles.row_hover = "rgb(50,50,50)"
        self.styles.row_selected = "rgb(60,60,100)"
        self.styles.row_cursor = "rgb(70,70,120)"

    def on_mount(self) -> None:
        self.cursor_type = "row"
        if self.row_count > 0:
            self.move_cursor(row=0, column=0)

    def populate(self, completions: list) -> None:
        self.clear()
        for completion in completions:
            name = completion.name
            type_ = completion.type
            info = completion.description or ""

            type_indicators = {
                "function": "🔧",
                "class": "📦",
                "module": "📚",
                "keyword": "🔑",
                "builtin": "⚡",
                "local": "📎",
                "method": "⚙️",
                "property": "🔹",
            }
            type_icon = type_indicators.get(type_, "•")
            self.add_row(f"{type_icon} {name}", type_, info)

        if self.row_count > 0:
            self.move_cursor(row=0, column=0)

    def on_key(self, event) -> None:
        if event.key == "tab":
            if self.cursor_row is not None:
                value = self.get_cell_at(Coordinate(self.cursor_row, 0))
                value = value.split(" ", 1)[1] if " " in value else value
                self.post_message(self.Selected(value))
            event.prevent_default()
            event.stop()
        elif event.key == "enter":
            # Enter should just hide the popup without selecting
            self.post_message(self.Selected(""))
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self.post_message(self.Selected(""))
            event.prevent_default()
            event.stop()
        elif event.key == "up":
            if self.cursor_row is not None and self.cursor_row > 0:
                self.move_cursor(row=self.cursor_row - 1, column=0)
            event.prevent_default()
            event.stop()
        elif event.key == "down":
            if self.cursor_row is not None and self.cursor_row < self.row_count - 1:
                self.move_cursor(row=self.cursor_row + 1, column=0)
            event.prevent_default()
            event.stop()


class CodeEditor(TextArea):

    class _LocalCompletion:
        def __init__(self, name: str):
            self.name = name
            self.type = "local"
            self.description = f"Local symbol: {name}"
            self.score = 0

    def _get_local_completions(self) -> list:
        # Cache local completions to avoid expensive regex on every keystroke
        if not hasattr(self, '_local_completions_cache') or self._text_changed_since_cache:
            pattern = re.compile(r"[A-Za-z_]\w*")
            tokens_found = set(pattern.findall(self.text))
            python_keywords = {
                "False", "None", "True", "and", "as", "assert", "async", "await",
                "break", "class", "continue", "def", "del", "elif", "else", "except",
                "finally", "for", "from", "global", "if", "import", "in", "is",
                "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
                "try", "while", "with", "yield",
            }
            tokens_found = tokens_found - python_keywords

            self._local_completions_cache = []
            for tok in sorted(tokens_found):
                if len(tok) > 1:  # Skip single-letter tokens
                    self._local_completions_cache.append(CodeEditor._LocalCompletion(tok))
            
            self._text_changed_since_cache = False

        return self._local_completions_cache

    BINDINGS = [
        Binding("ctrl+n", "new_file", "New File", show=True),
        Binding("tab", "indent_or_complete", "Indent/Complete", show=False),
        Binding("shift+tab", "unindent", "Unindent", show=False),
        Binding("ctrl+]", "indent", "Indent", show=False),
        Binding("ctrl+[", "unindent", "Unindent", show=False),
        Binding("ctrl+s", "save_file", "Save File", show=True),
        Binding("escape", "enter_normal_mode", "Enter Normal Mode", show=False),
        Binding("i", "enter_insert_mode", "Enter Insert Mode", show=False),
        Binding("a", "enter_insert_mode_after", "Insert After", show=False),
        Binding("A", "enter_insert_mode_end", "Insert at End", show=False),
        Binding("o", "open_line_below", "Open Line Below", show=False),
        Binding("O", "open_line_above", "Open Line Above", show=False),
        Binding("h", "move_left", "Move Left", show=False),
        Binding("l", "move_right", "Move Right", show=False),
        Binding("j", "move_down", "Move Down", show=False),
        Binding("k", "move_up", "Move Up", show=False),
        Binding("w", "move_word_forward", "Move Word Forward", show=False),
        Binding("b", "move_word_backward", "Move Word Backward", show=False),
        Binding("e", "move_word_end", "Move to Word End", show=False),
        Binding("0", "move_line_start", "Move to Line Start", show=False),
        Binding("^", "move_line_first_char", "Move to First Non-blank", show=False),
        Binding("$", "move_line_end", "Move to Line End", show=False),
        Binding("g", "vim_g_commands", "G Commands", show=False),
        Binding("shift+left", "focus_tree", "Focus Tree", show=True),
        Binding("u", "undo", "Undo", show=False),
        Binding("ctrl+r", "redo", "Redo", show=False),
        Binding("x", "delete_char", "Delete Character", show=False),
        Binding("d", "vim_delete", "Delete", show=False),
        Binding("c", "vim_change", "Change", show=False),
        Binding("y", "vim_yank", "Yank", show=False),
        Binding("p", "vim_paste", "Paste", show=False),
        Binding("v", "enter_visual_mode", "Visual Mode", show=False),
        Binding("shift+v", "enter_visual_line_mode", "Visual Line Mode", show=False),
        Binding(".", "repeat_last_action", "Repeat", show=False),
        Binding("ctrl+space", "show_completions", "Show Completions", show=True),
        Binding("ctrl+z", "noop", ""),
        Binding("ctrl+y", "noop", ""),
    ]

    class FileModified(Message):
        def __init__(self, is_modified: bool) -> None:
            super().__init__()
            self.is_modified = is_modified

        def action_noop(self) -> None:
            pass

    def __init__(self) -> None:
        super().__init__(language="python", theme="monokai", show_line_numbers=True)
        self.current_file = None
        self._modified = False
        self.tab_size = 4
        self._syntax = None
        self.language = None
        self.highlight_text = None
        
        # Vim state
        self.mode = "normal"
        self._vim_command = ""
        self._vim_count = ""
        self._pending_operator = ""
        self._visual_start = None
        self._visual_mode = None  # None, 'char', 'line'
        self._last_action = None
        self._registers = {}  # Vim registers
        
        # Completion state
        self._completion_popup = None
        self._completion_debounce_timer = None
        self._local_completions_cache = []
        self._text_changed_since_cache = True
        
        # Editor state
        self._last_text = ""
        self._is_undoing = False
        self.command = ""
        self.in_command_mode = False
        self.pending_command = ""
        self.status_bar = StatusBar()
        self.status_bar.update_mode("NORMAL")
        self.tabs = []
        self.active_tab_index = -1
        self.autopairs = {"{": "}", "(": ")", "[": "]", '"': '"', "'": "'"}
        self._word_pattern = re.compile(r"[\w\.]")

        # Built-in completions (cached)
        self._builtins = {
            "print": ("function", "Print objects to the text stream"),
            "len": ("function", "Return the length of an object"),
            "str": ("function", "Return a string version of an object"),
            "int": ("function", "Convert a number or string to an integer"),
            "list": ("function", "Create a new list"),
            "dict": ("function", "Create a new dictionary"),
            "range": ("function", "Create a sequence of numbers"),
            "open": ("function", "Open a file"),
            "type": ("function", "Return the type of an object"),
            "input": ("function", "Read a string from standard input"),
            "float": ("function", "Convert a number or string to a float"),
            "bool": ("function", "Convert a value to a Boolean"),
            "set": ("function", "Create a new set"),
            "tuple": ("function", "Create a new tuple"),
            "enumerate": ("function", "Return an enumerate object"),
            "zip": ("function", "Aggregate elements from iterables"),
            "max": ("function", "Return the largest item"),
            "min": ("function", "Return the smallest item"),
            "sum": ("function", "Sum values in an iterable"),
            "sorted": ("function", "Return a sorted list"),
            "reversed": ("function", "Return a reverse iterator"),
            "any": ("function", "Return True if any element is true"),
            "all": ("function", "Return True if all elements are true"),
            "map": ("function", "Apply function to every item"),
            "filter": ("function", "Filter elements from iterable"),
        }

        self._common_patterns = {
            "if ": ("keyword", "Start an if statement"),
            "for ": ("keyword", "Start a for loop"),
            "while ": ("keyword", "Start a while loop"),
            "def ": ("keyword", "Define a function"),
            "class ": ("keyword", "Define a class"),
            "import ": ("keyword", "Import a module"),
            "from ": ("keyword", "Import specific names from a module"),
            "return ": ("keyword", "Return from a function"),
            "try": ("keyword", "Start a try-except block"),
            "with ": ("keyword", "Context manager statement"),
            "elif ": ("keyword", "Else if condition"),
            "except ": ("keyword", "Exception handler"),
            "finally": ("keyword", "Finally block"),
            "async def ": ("keyword", "Define async function"),
            "await ": ("keyword", "Await async operation"),
        }

        self._common_imports = {
            "os": "Operating system interface",
            "sys": "System-specific parameters and functions",
            "json": "JSON encoder and decoder",
            "datetime": "Basic date and time types",
            "random": "Generate random numbers",
            "math": "Mathematical functions",
            "pathlib": "Object-oriented filesystem paths",
            "typing": "Support for type hints",
            "collections": "Container datatypes",
            "re": "Regular expression operations",
            "itertools": "Functions creating iterators",
            "functools": "Higher-order functions and operations",
            "subprocess": "Subprocess management",
            "urllib": "URL handling modules",
            "requests": "HTTP library",
            "pandas": "Data analysis library",
            "numpy": "Numerical computing",
        }

    def _save_positions(self) -> None:
        self._last_scroll_position = self.scroll_offset
        self._last_cursor_position = self.cursor_location

    def _restore_positions(self) -> None:
        self.scroll_to(self._last_scroll_position[0], self._last_scroll_position[1])
        self.move_cursor(self._last_cursor_position)

    def compose(self) -> ComposeResult:
        yield self.status_bar

    def on_mount(self) -> None:
        self.status_bar.update_mode("NORMAL")
        self._update_status_info()

    def _update_status_info(self) -> None:
        file_info = []
        if self.tabs:
            file_info.append(f"[{self.active_tab_index + 1}/{len(self.tabs)}]")
        if self.current_file:
            file_info.append(os.path.basename(str(self.current_file)))
        if self._modified:
            file_info.append("[bold red][+][/]")
        if self.text:
            lines = len(self.text.split("\n"))
            chars = len(self.text)
            file_info.append(f"{lines}L, {chars}B")

        # Show vim command if any
        command_info = ""
        if self._vim_count:
            command_info += self._vim_count
        if self._pending_operator:
            command_info += self._pending_operator
        if self._vim_command:
            command_info += self._vim_command
        
        if command_info:
            file_info.append(f"[bold cyan]{command_info}[/]")

        self.status_bar.update_file_info(" ".join(file_info))

    def _get_current_undo_stack(self) -> list:
        """Get the undo stack for the current buffer."""
        if self.tabs and self.active_tab_index >= 0:
            return self.tabs[self.active_tab_index].undo_stack
        return []
    
    def _get_current_redo_stack(self) -> list:
        """Get the redo stack for the current buffer."""
        if self.tabs and self.active_tab_index >= 0:
            return self.tabs[self.active_tab_index].redo_stack
        return []
    
    def _save_buffer_state(self) -> None:
        """Save current cursor and scroll position to the active buffer."""
        if self.tabs and self.active_tab_index >= 0:
            tab = self.tabs[self.active_tab_index]
            tab.cursor_position = self.cursor_location
            tab.scroll_position = self.scroll_offset
            tab.content = self.text
            tab.modified = self._modified
    
    def _restore_buffer_state(self) -> None:
        """Restore cursor and scroll position from the active buffer."""
        if self.tabs and self.active_tab_index >= 0:
            tab = self.tabs[self.active_tab_index]
            self.move_cursor(tab.cursor_position)
            self.scroll_to(tab.scroll_position[0], tab.scroll_position[1], animate=False)

    def _save_undo_state(self, text: str = None) -> None:
        """Save state to undo stack of the current buffer."""
        if not self._is_undoing and self.tabs and self.active_tab_index >= 0:
            tab = self.tabs[self.active_tab_index]
            
            # Use provided text or current text
            state_text = text if text is not None else self.text
            
            # Don't save if this is the same as the last undo state
            if tab.undo_stack and tab.undo_stack[-1]["text"] == state_text:
                return
            
            # Create undo state
            undo_state = {
                "text": state_text,
                "cursor": self.cursor_location,
                "scroll": self.scroll_offset,
            }
            
            # Add to this buffer's undo stack
            tab.undo_stack.append(undo_state)
            
            # Limit undo stack size to prevent memory issues
            if len(tab.undo_stack) > 100:
                tab.undo_stack.pop(0)
            
            # Clear redo stack when new change is made
            tab.redo_stack.clear()

    def _move_cursor_preserve_scroll(self, position: tuple[int, int]) -> None:
        """Move cursor while preserving scroll position to prevent viewport jumps."""
        current_scroll = self.scroll_offset
        self.move_cursor(position)
        # Always restore scroll position to prevent viewport jumping
        self.scroll_to(current_scroll[0], current_scroll[1], animate=False)

    def _trigger_completions(self) -> None:
        """Trigger completion popup if appropriate."""
        try:
            current_word, _ = self._get_current_word()
            
            # Get completions
            completions = self._get_completions()
            
            if completions:
                # Show popup
                if not self._completion_popup:
                    row, col = self.cursor_location
                    popup = AutoCompletePopup()
                    popup.populate(completions)
                    popup.styles.offset = (col, row + 1)
                    self._completion_popup = popup
                    self.mount(popup)
                else:
                    self._completion_popup.populate(completions)
            else:
                # Hide popup if no completions
                if self._completion_popup:
                    self.hide_completions()
        except Exception as e:
            self.notify(f"Completion error: {str(e)}", severity="error", timeout=2)

    def _debounced_completion_update(self) -> None:
        """Update completions immediately - removed debouncing as it was causing issues."""
        if self.mode == "insert" and self._completion_popup:
            completions = self._get_completions()
            if completions:
                self._completion_popup.populate(completions)
            else:
                self.hide_completions()

    def _vim_execute_motion(self, motion: str, count: int = 1) -> tuple[int, int]:
        """Execute a vim motion and return the new cursor position."""
        current_row, current_col = self.cursor_location
        lines = self.text.split("\n")
        
        for _ in range(count):
            if motion == "h":
                if current_col > 0:
                    current_col -= 1
            elif motion == "l":
                if current_row < len(lines) and current_col < len(lines[current_row]):
                    current_col += 1
            elif motion == "j":
                if current_row < len(lines) - 1:
                    current_row += 1
                    current_col = min(current_col, len(lines[current_row]))
            elif motion == "k":
                if current_row > 0:
                    current_row -= 1
                    current_col = min(current_col, len(lines[current_row]))
            elif motion == "w":
                # Move to start of next word
                if current_row < len(lines):
                    line = lines[current_row]
                    while current_col < len(line) and not line[current_col].isalnum() and line[current_col] != "_":
                        current_col += 1
                    while current_col < len(line) and (line[current_col].isalnum() or line[current_col] == "_"):
                        current_col += 1
                    if current_col >= len(line) and current_row < len(lines) - 1:
                        current_row += 1
                        current_col = 0
            elif motion == "b":
                # Move to start of previous word
                if current_col > 0:
                    current_col -= 1
                    line = lines[current_row]
                    while current_col > 0 and not (line[current_col].isalnum() or line[current_col] == "_"):
                        current_col -= 1
                    while current_col > 0 and (line[current_col - 1].isalnum() or line[current_col - 1] == "_"):
                        current_col -= 1
                elif current_row > 0:
                    current_row -= 1
                    current_col = len(lines[current_row])
            elif motion == "e":
                # Move to end of current/next word
                if current_row < len(lines):
                    line = lines[current_row]
                    if current_col < len(line) and (line[current_col].isalnum() or line[current_col] == "_"):
                        while current_col < len(line) - 1 and (line[current_col + 1].isalnum() or line[current_col + 1] == "_"):
                            current_col += 1
                    else:
                        while current_col < len(line) and not (line[current_col].isalnum() or line[current_col] == "_"):
                            current_col += 1
                        while current_col < len(line) - 1 and (line[current_col + 1].isalnum() or line[current_col + 1] == "_"):
                            current_col += 1
            elif motion == "0":
                current_col = 0
            elif motion == "^":
                line = lines[current_row] if current_row < len(lines) else ""
                current_col = 0
                while current_col < len(line) and line[current_col].isspace():
                    current_col += 1
            elif motion == "$":
                if current_row < len(lines):
                    current_col = len(lines[current_row])
            elif motion == "gg":
                current_row = 0
                current_col = 0
            elif motion == "G":
                current_row = len(lines) - 1
                current_col = 0
                
        return current_row, current_col

    def _vim_get_text_range(self, start_pos: tuple[int, int], end_pos: tuple[int, int]) -> str:
        """Get text between two positions."""
        start_row, start_col = start_pos
        end_row, end_col = end_pos
        
        if start_row == end_row:
            line = self.text.split("\n")[start_row]
            return line[start_col:end_col]
        
        lines = self.text.split("\n")
        result = []
        
        # First line
        result.append(lines[start_row][start_col:])
        
        # Middle lines
        for row in range(start_row + 1, end_row):
            result.append(lines[row])
        
        # Last line
        if end_row < len(lines):
            result.append(lines[end_row][:end_col])
        
        return "\n".join(result)

    def _vim_delete_range(self, start_pos: tuple[int, int], end_pos: tuple[int, int]) -> str:
        """Delete text between two positions and return the deleted text."""
        # Save current scroll position
        current_scroll = self.scroll_offset
        
        deleted_text = self._vim_get_text_range(start_pos, end_pos)
        
        start_row, start_col = start_pos
        end_row, end_col = end_pos
        
        lines = self.text.split("\n")
        
        if start_row == end_row:
            lines[start_row] = lines[start_row][:start_col] + lines[start_row][end_col:]
        else:
            # Combine first and last line
            lines[start_row] = lines[start_row][:start_col] + (lines[end_row][end_col:] if end_row < len(lines) else "")
            # Remove lines in between
            for _ in range(end_row - start_row):
                if start_row + 1 < len(lines):
                    lines.pop(start_row + 1)
        
        self.text = "\n".join(lines)
        self.move_cursor(start_pos)
        # Restore scroll position to keep viewport stable
        self.scroll_to(current_scroll[0], current_scroll[1], animate=False)
        return deleted_text

    def get_current_indent(self) -> str:
        lines = self.text.split("\n")
        if not lines:
            return ""
        current_line = lines[self.cursor_location[0]]
        indent = ""
        for char in current_line:
            if char.isspace():
                indent += char
            else:
                break
        return indent

    def should_increase_indent(self) -> bool:
        lines = self.text.split("\n")
        if not lines:
            return False
        current_line = lines[self.cursor_location[0]]
        stripped_line = current_line.strip()

        if stripped_line.endswith(":"):
            return True

        brackets = {"(": ")", "[": "]", "{": "}"}
        counts = {
            k: stripped_line.count(k) - stripped_line.count(v)
            for k, v in brackets.items()
        }
        return any(count > 0 for count in counts.values())

    def should_decrease_indent(self) -> bool:
        lines = self.text.split("\n")
        if not lines or self.cursor_location[0] == 0:
            return False

        current_line = lines[self.cursor_location[0]]
        stripped_line = current_line.strip()

        if stripped_line.startswith((")", "]", "}")):
            return True

        dedent_keywords = {"return", "break", "continue", "pass", "raise"}
        first_word = stripped_line.split()[0] if stripped_line else ""
        return first_word in dedent_keywords

    def handle_indent(self) -> None:
        current_indent = self.get_current_indent()
        lines = self.text.split("\n")
        current_line = lines[self.cursor_location[0]] if lines else ""
        cursor_col = self.cursor_location[1]

        if cursor_col > 0 and cursor_col < len(current_line):
            prev_char = current_line[cursor_col - 1]
            next_char = current_line[cursor_col]
            bracket_pairs = {"{": "}", "(": ")", "[": "]"}

            if prev_char in bracket_pairs and next_char == bracket_pairs[prev_char]:
                indent_level = current_indent + " " * self.tab_size
                self.insert(f"\n{indent_level}\n{current_indent}")
                self._move_cursor_preserve_scroll((self.cursor_location[0] - 1, len(indent_level)))
                return

        if not current_indent and not self.text:
            self.insert("\n")
            return

        if self.should_decrease_indent():
            new_indent = (
                current_indent[: -self.tab_size]
                if len(current_indent) >= self.tab_size
                else ""
            )
            self.insert("\n" + new_indent)
        elif self.should_increase_indent():
            self.insert("\n" + current_indent + " " * self.tab_size)
        else:
            self.insert("\n" + current_indent)

    def handle_backspace(self) -> None:
        if not self.text:
            return

        cur_row, cur_col = self.cursor_location
        lines = self.text.split("\n")
        if cur_row >= len(lines):
            return

        current_line = lines[cur_row]

        if cur_col >= 1 and cur_col < len(current_line) + 1:
            prev_char = current_line[cur_col - 1]
            if prev_char in self.autopairs:
                if (
                    cur_col < len(current_line)
                    and current_line[cur_col] == self.autopairs[prev_char]
                ):
                    lines[cur_row] = (
                        current_line[: cur_col - 1] + current_line[cur_col + 1 :]
                    )
                    self.text = "\n".join(lines)
                    self._move_cursor_preserve_scroll((cur_row, cur_col - 1))
                    return

        if cur_col == 0 and cur_row > 0:
            self.action_delete_left()
            return

        prefix = current_line[:cur_col]
        if prefix.isspace():
            spaces_to_delete = min(self.tab_size, len(prefix.rstrip()) or len(prefix))
            for _ in range(spaces_to_delete):
                self.action_delete_left()
        else:
            self.action_delete_left()

    def on_key(self, event) -> None:
        # Handle completion popup navigation first
        if self._completion_popup and event.key in ["up", "down", "tab", "enter", "escape"]:
            if event.key == "tab":
                # Only tab selects completion - enter just closes popup
                if self._completion_popup.row_count > 0:
                    selected_row = self._completion_popup.cursor_row or 0
                    value = self._completion_popup.get_cell_at(Coordinate(selected_row, 0))
                    value = value.split(" ", 1)[1] if " " in value else value

                    lines = self.text.split("\n")
                    row, col = self.cursor_location
                    current_word, word_start = self._get_current_word()
                    line = lines[row]
                    lines[row] = line[:word_start] + value + line[col:]
                    self.text = "\n".join(lines)
                    self._move_cursor_preserve_scroll((row, word_start + len(value)))
                self.hide_completions()
                event.prevent_default()
                event.stop()
                return
            elif event.key == "enter":
                # Enter just closes the popup without selecting
                self.hide_completions()
                # Let the enter key continue to normal handling
            elif event.key == "escape":
                self.hide_completions()
                if self.mode != "normal":
                    return
            elif event.key in ["up", "down"]:
                self._completion_popup.focus()
                event.prevent_default()
                event.stop()
                return

        # Command mode handling
        if self.in_command_mode:
            if event.key == "enter":
                self.execute_command()
                self.in_command_mode = False
                self.command = ""
                self.status_bar.update_mode(self.mode.upper())
                self.status_bar.update_command("")
            elif event.key == "escape":
                self.in_command_mode = False
                self.command = ""
                self.status_bar.update_mode(self.mode.upper())
                self.status_bar.update_command("")
            elif event.key == "backspace":
                if len(self.command) > 1:
                    self.command = self.command[:-1]
                else:
                    self.in_command_mode = False
                    self.command = ""
                self.status_bar.update_command(self.command)
            elif event.is_printable:
                self.command += event.character
                self.status_bar.update_command(self.command)
            event.prevent_default()
            event.stop()
            return

        # Mode-specific handling
        if self.mode == "insert":
            self._handle_insert_mode(event)
        elif self.mode == "normal":
            self._handle_normal_mode(event)
        elif self.mode == "visual":
            self._handle_visual_mode(event)

    def _handle_insert_mode(self, event) -> None:
        if event.key == "escape":
            self.action_enter_normal_mode()
            event.prevent_default()
            event.stop()
        elif event.key == "enter":
            self._save_undo_state(self.text)  # Save state before change
            self.handle_indent()
            self._modified = True
            self.post_message(self.FileModified(True))
            event.prevent_default()
            event.stop()
        elif event.key == "tab":
            # If we get here, there's no completion popup visible, so do normal indentation
            self._save_undo_state(self.text)  # Save state before change
            self.action_indent()
            event.prevent_default()
            event.stop()
        elif event.key == "backspace":
            self._save_undo_state(self.text)  # Save state before change
            self.handle_backspace()
            self._modified = True
            self.post_message(self.FileModified(True))
            event.prevent_default()
            event.stop()
        elif event.is_printable:
            self._save_undo_state(self.text)  # Save state before change
            
            # Handle autopairs
            if event.character in self.autopairs:
                cur_pos = self.cursor_location
                self.insert(event.character + self.autopairs[event.character])
                self._move_cursor_preserve_scroll((cur_pos[0], cur_pos[1] + 1))
            else:
                self.insert(event.character)
            
            self._modified = True
            self._text_changed_since_cache = True
            self.post_message(self.FileModified(True))
            
            # Always trigger completion check when typing
            self._trigger_completions()
            
            event.prevent_default()
            event.stop()

    def _handle_normal_mode(self, event) -> None:
        char = event.character if event.is_printable else event.key

        # Handle number prefixes for counts
        if char.isdigit() and (self._vim_count or char != "0"):
            self._vim_count += char
            self._update_status_info()
            event.prevent_default()
            event.stop()
            return

        count = int(self._vim_count) if self._vim_count else 1

        # Handle operators
        if self._pending_operator:
            if char in ["d", "c", "y"]:  # dd, cc, yy
                if char == self._pending_operator:
                    self._vim_execute_operator_line(self._pending_operator, count)
                    self._clear_vim_state()
                    event.prevent_default()
                    event.stop()
                    return
            else:
                # Motion after operator
                if self._vim_execute_operator_motion(self._pending_operator, char, count):
                    self._clear_vim_state()
                    event.prevent_default()
                    event.stop()
                    return
                else:
                    self._clear_vim_state()

        # Basic motions
        elif char in ["h", "j", "k", "l", "w", "b", "e", "0", "^", "$"]:
            new_pos = self._vim_execute_motion(char, count)
            self._move_cursor_preserve_scroll(new_pos)
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        
        # Special motions
        elif char == "g":
            if self._vim_command == "g":
                # gg - go to top (preserve scroll unless explicitly going to top)
                if count == 1:
                    # Normal gg - go to top and reset scroll to show beginning
                    self.move_cursor((0, 0))
                    self.scroll_to(0, 0, animate=False)
                else:
                    # Line number - preserve scroll position
                    line_num = min(count - 1, len(self.text.split("\n")) - 1)
                    self._move_cursor_preserve_scroll((line_num, 0))
                self._clear_vim_state()
            else:
                self._vim_command = "g"
                self._update_status_info()
            event.prevent_default()
            event.stop()
            
        elif char == "G":
            lines = self.text.split("\n")
            if self._vim_count:
                line_num = min(count - 1, len(lines) - 1)
                self._move_cursor_preserve_scroll((line_num, 0))
            else:
                # Go to end - show end of file
                self.move_cursor((len(lines) - 1, 0))
                # Scroll to show the end
                self.scroll_to(max(0, len(lines) - 20), 0, animate=False)
            self._clear_vim_state()
            event.prevent_default()
            event.stop()

        # Insert mode entries
        elif char == "i":
            self.action_enter_insert_mode()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        elif char == "a":
            self.action_enter_insert_mode_after()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        elif char == "A":
            self.action_enter_insert_mode_end()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        elif char == "o":
            self.action_open_line_below()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        elif char == "O":
            self.action_open_line_above()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()

        # Operators
        elif char in ["d", "c", "y"]:
            self._pending_operator = char
            self._update_status_info()
            event.prevent_default()
            event.stop()

        # Simple actions
        elif char == "x":
            self._vim_delete_char(count)
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        elif char == "p":
            self._vim_paste_after()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        elif char == "P":
            self._vim_paste_before()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()

        # Visual mode
        elif char == "v":
            self.action_enter_visual_mode()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        elif char == "V":
            self.action_enter_visual_line_mode()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()

        # Other commands
        elif char == "u":
            self.action_undo()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        elif event.key == "ctrl+r":
            self.action_redo()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        elif char == ".":
            self._vim_repeat_last_action()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        elif char == ":":
            self.in_command_mode = True
            self.command = ":"
            self.status_bar.update_mode("COMMAND")
            self.status_bar.update_command(self.command)
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        elif event.key == "ctrl+space":
            self.action_show_completions()
            self._clear_vim_state()
            event.prevent_default()
            event.stop()
        else:
            self._clear_vim_state()

    def _handle_visual_mode(self, event) -> None:
        char = event.character if event.is_printable else event.key
        count = int(self._vim_count) if self._vim_count else 1

        # Handle number prefixes for counts in visual mode
        if char and char.isdigit() and (self._vim_count or char != "0"):
            self._vim_count += char
            self._update_status_info()
            event.prevent_default()
            event.stop()
            return

        if char == "escape" or event.key == "escape":
            self.action_enter_normal_mode()
            event.prevent_default()
            event.stop()
        elif char in ["d", "x"]:
            try:
                self._vim_visual_delete()
                self.action_enter_normal_mode()
            except Exception as e:
                self.notify(f"Delete error: {str(e)}", severity="error")
                self.action_enter_normal_mode()
            event.prevent_default()
            event.stop()
        elif char == "y":
            try:
                self._vim_visual_yank()
                self.action_enter_normal_mode()
            except Exception as e:
                self.notify(f"Yank error: {str(e)}", severity="error")
                self.action_enter_normal_mode()
            event.prevent_default()
            event.stop()
        elif char == "c":
            try:
                self._vim_visual_change()
            except Exception as e:
                self.notify(f"Change error: {str(e)}", severity="error")
                self.action_enter_normal_mode()
            event.prevent_default()
            event.stop()
        elif char in ["h", "j", "k", "l", "w", "b", "e", "0", "^", "$"]:
            try:
                new_pos = self._vim_execute_motion(char, count)
                self._move_cursor_preserve_scroll(new_pos)
                self._update_visual_selection()
                self._clear_vim_state()  # Clear count after motion
            except Exception as e:
                self.notify(f"Motion error: {str(e)}", severity="error")
                self.action_enter_normal_mode()
            event.prevent_default()
            event.stop()
        else:
            # For unhandled keys, clear the count and ignore
            self._vim_count = ""
            self._update_status_info()
            event.prevent_default()
            event.stop()

    def _clear_vim_state(self) -> None:
        self._vim_count = ""
        self._vim_command = ""
        self._pending_operator = ""
        self._update_status_info()

    # Vim action methods
    def action_enter_insert_mode_after(self) -> None:
        """Enter insert mode after cursor (a command)."""
        row, col = self.cursor_location
        lines = self.text.split("\n")
        if row < len(lines) and col < len(lines[row]):
            self._move_cursor_preserve_scroll((row, col + 1))
        self.action_enter_insert_mode()

    def action_enter_insert_mode_end(self) -> None:
        """Enter insert mode at end of line (A command)."""
        row, col = self.cursor_location
        lines = self.text.split("\n")
        if row < len(lines):
            self._move_cursor_preserve_scroll((row, len(lines[row])))
        self.action_enter_insert_mode()

    def action_open_line_below(self) -> None:
        """Open new line below cursor (o command)."""
        # Save undo state before making changes
        self._save_undo_state(self.text)
        
        row, col = self.cursor_location
        lines = self.text.split("\n")
        indent = self.get_current_indent()
        lines.insert(row + 1, indent)
        self.text = "\n".join(lines)
        self._move_cursor_preserve_scroll((row + 1, len(indent)))
        self.action_enter_insert_mode()

    def action_open_line_above(self) -> None:
        """Open new line above cursor (O command)."""
        # Save undo state before making changes
        self._save_undo_state(self.text)
        
        row, col = self.cursor_location
        lines = self.text.split("\n")
        indent = self.get_current_indent()
        lines.insert(row, indent)
        self.text = "\n".join(lines)
        self._move_cursor_preserve_scroll((row, len(indent)))
        self.action_enter_insert_mode()

    def action_enter_visual_mode(self) -> None:
        """Enter visual character mode."""
        self.mode = "visual"
        self._visual_start = self.cursor_location
        self._visual_mode = "char"
        self.status_bar.update_mode("VISUAL")

    def action_enter_visual_line_mode(self) -> None:
        """Enter visual line mode."""
        self.mode = "visual"  # Use same mode as regular visual
        self._visual_start = self.cursor_location
        self._visual_mode = "line"
        self.status_bar.update_mode("VISUAL LINE")

    def _update_visual_selection(self) -> None:
        """Update visual selection highlighting."""
        # This would need to be implemented with textual's highlighting system
        pass

    def _vim_execute_operator_line(self, operator: str, count: int) -> None:
        """Execute operator on whole lines (dd, cc, yy)."""
        # Save undo state before making changes
        if operator in ["d", "c"]:  # Only for destructive operations
            self._save_undo_state(self.text)
        
        # Save current scroll position
        current_scroll = self.scroll_offset
        row, col = self.cursor_location
        lines = self.text.split("\n")
        
        start_row = row
        end_row = min(row + count, len(lines))
        
        # Get text to operate on
        deleted_lines = lines[start_row:end_row]
        deleted_text = "\n".join(deleted_lines)
        
        if operator == "d":  # Delete lines
            self._registers["\""] = deleted_text + "\n"
            for _ in range(count):
                if start_row < len(lines):
                    lines.pop(start_row)
            if start_row >= len(lines) and lines:
                start_row = len(lines) - 1
            self.text = "\n".join(lines)
            self.move_cursor((start_row, 0))
            # Restore scroll position to keep viewport stable
            self.scroll_to(current_scroll[0], current_scroll[1], animate=False)
            
        elif operator == "y":  # Yank lines
            self._registers["\""] = deleted_text + "\n"
            # Keep cursor and scroll position for yank
            
        elif operator == "c":  # Change lines
            self._registers["\""] = deleted_text + "\n"
            indent = self.get_current_indent()
            for _ in range(count):
                if start_row < len(lines):
                    lines.pop(start_row)
            lines.insert(start_row, indent)
            self.text = "\n".join(lines)
            self.move_cursor((start_row, len(indent)))
            # Restore scroll position before entering insert mode
            self.scroll_to(current_scroll[0], current_scroll[1], animate=False)
            self.action_enter_insert_mode()

        self._last_action = ("operator_line", operator, count)

    def _vim_execute_operator_motion(self, operator: str, motion: str, count: int) -> bool:
        """Execute operator with motion (dw, c$, etc)."""
        # Save undo state before making changes
        if operator in ["d", "c"]:  # Only for destructive operations
            self._save_undo_state(self.text)
        
        start_pos = self.cursor_location
        end_pos = self._vim_execute_motion(motion, count)
        
        if start_pos == end_pos:
            return False
        
        # Ensure start is before end
        if start_pos > end_pos:
            start_pos, end_pos = end_pos, start_pos
        
        if operator == "d":  # Delete
            deleted_text = self._vim_delete_range(start_pos, end_pos)
            self._registers["\""] = deleted_text
            
        elif operator == "y":  # Yank
            yanked_text = self._vim_get_text_range(start_pos, end_pos)
            self._registers["\""] = yanked_text
            
        elif operator == "c":  # Change
            deleted_text = self._vim_delete_range(start_pos, end_pos)
            self._registers["\""] = deleted_text
            self.action_enter_insert_mode()

        self._last_action = ("operator_motion", operator, motion, count)
        return True

    def _vim_delete_char(self, count: int) -> None:
        """Delete character(s) under cursor (x command)."""
        # Save undo state before making changes
        self._save_undo_state(self.text)
        
        # Save current scroll position
        current_scroll = self.scroll_offset
        
        row, col = self.cursor_location
        lines = self.text.split("\n")
        
        if row < len(lines):
            line = lines[row]
            end_col = min(col + count, len(line))
            deleted = line[col:end_col]
            lines[row] = line[:col] + line[end_col:]
            self.text = "\n".join(lines)
            self._registers["\""] = deleted
            # Restore scroll position to keep viewport stable
            self.scroll_to(current_scroll[0], current_scroll[1], animate=False)

        self._last_action = ("delete_char", count)

    def _vim_paste_after(self) -> None:
        """Paste after cursor (p command)."""
        if "\"" not in self._registers:
            return
        
        # Save undo state before making changes
        self._save_undo_state(self.text)
            
        text_to_paste = self._registers["\""]
        row, col = self.cursor_location
        
        if text_to_paste.endswith("\n"):  # Line paste
            lines = self.text.split("\n")
            paste_lines = text_to_paste.rstrip("\n").split("\n")
            for i, line in enumerate(paste_lines):
                lines.insert(row + 1 + i, line)
            self.text = "\n".join(lines)
            self.move_cursor((row + 1, 0))
        else:  # Character paste
            lines = self.text.split("\n")
            if row < len(lines):
                line = lines[row]
                insert_pos = min(col + 1, len(line))
                lines[row] = line[:insert_pos] + text_to_paste + line[insert_pos:]
                self.text = "\n".join(lines)
                self.move_cursor((row, insert_pos + len(text_to_paste) - 1))

    def _vim_paste_before(self) -> None:
        """Paste before cursor (P command)."""
        if "\"" not in self._registers:
            return
        
        # Save undo state before making changes
        self._save_undo_state(self.text)
            
        text_to_paste = self._registers["\""]
        row, col = self.cursor_location
        
        if text_to_paste.endswith("\n"):  # Line paste
            lines = self.text.split("\n")
            paste_lines = text_to_paste.rstrip("\n").split("\n")
            for i, line in enumerate(paste_lines):
                lines.insert(row + i, line)
            self.text = "\n".join(lines)
            self.move_cursor((row, 0))
        else:  # Character paste
            lines = self.text.split("\n")
            if row < len(lines):
                line = lines[row]
                lines[row] = line[:col] + text_to_paste + line[col:]
                self.text = "\n".join(lines)
                self.move_cursor((row, col + len(text_to_paste) - 1))

    def _vim_visual_delete(self) -> None:
        """Delete visual selection."""
        if self._visual_start is None:
            return
        
        # Save undo state before making changes
        self._save_undo_state(self.text)
            
        start_pos = self._visual_start
        end_pos = self.cursor_location
        
        if start_pos > end_pos:
            start_pos, end_pos = end_pos, start_pos
            
        if self._visual_mode == "line":
            # Delete whole lines
            start_row, _ = start_pos
            end_row, _ = end_pos
            self._vim_execute_operator_line("d", end_row - start_row + 1)
        else:
            # Delete character range
            deleted_text = self._vim_delete_range(start_pos, (end_pos[0], end_pos[1] + 1))
            self._registers["\""] = deleted_text

    def _vim_visual_yank(self) -> None:
        """Yank visual selection."""
        if self._visual_start is None:
            return
            
        start_pos = self._visual_start
        end_pos = self.cursor_location
        
        if start_pos > end_pos:
            start_pos, end_pos = end_pos, start_pos
            
        if self._visual_mode == "line":
            # Yank whole lines
            start_row, _ = start_pos
            end_row, _ = end_pos
            lines = self.text.split("\n")
            yanked_lines = lines[start_row:end_row + 1]
            self._registers["\""] = "\n".join(yanked_lines) + "\n"
        else:
            # Yank character range
            yanked_text = self._vim_get_text_range(start_pos, (end_pos[0], end_pos[1] + 1))
            self._registers["\""] = yanked_text

    def _vim_visual_change(self) -> None:
        """Change visual selection."""
        # Use visual delete which already handles undo state
        self._vim_visual_delete()
        self.action_enter_insert_mode()

    def _vim_repeat_last_action(self) -> None:
        """Repeat last action (. command)."""
        if not self._last_action:
            return
            
        # Save undo state before repeating action
        self._save_undo_state(self.text)
            
        action_type = self._last_action[0]
        
        if action_type == "operator_line":
            _, operator, count = self._last_action
            self._vim_execute_operator_line(operator, count)
        elif action_type == "operator_motion":
            _, operator, motion, count = self._last_action
            self._vim_execute_operator_motion(operator, motion, count)
        elif action_type == "delete_char":
            _, count = self._last_action
            self._vim_delete_char(count)

    def action_indent_or_complete(self) -> None:
        """Smart tab: complete if popup open, otherwise indent."""
        # This action is now handled directly in the on_key method
        # Keeping for backward compatibility but delegating to indent
        self.action_indent()

    def _get_current_word(self) -> tuple[str, int]:
        row, col = self.cursor_location
        if not self.text:
            return "", col

        lines = self.text.split("\n")
        if row >= len(lines):
            return "", col

        line = lines[row]
        if not line:
            return "", col

        word_start = col
        while word_start > 0 and re.match(r"\w", line[word_start - 1]):
            word_start -= 1

        last_dot = line.rfind(".", word_start, col)
        if last_dot != -1:
            word_start = last_dot + 1

        current_word = line[word_start:col]
        return current_word, word_start

    def _get_completions(self) -> list:
        try:
            current_word, _ = self._get_current_word()
            
            suggestions = []
            seen = set()

            # If no word typed yet, show common keywords and builtins
            if len(current_word) == 0:
                # Show Python keywords
                keywords = ["print", "len", "str", "int", "list", "dict", "if", "for", "while", "def", "class", "import", "from", "return"]
                for keyword in keywords:
                    comp = self._create_completion(keyword, "keyword", f"Python keyword/builtin: {keyword}")
                    comp.score = 1000
                    suggestions.append(comp)
                    seen.add(keyword)
                return suggestions[:10]

            # Builtins - most relevant
            for name, (type_, desc) in self._builtins.items():
                if name.startswith(current_word):
                    comp = self._create_completion(name, "builtin", desc)
                    comp.score = 1000
                    suggestions.append(comp)
                    seen.add(name)

            # Context suggestions - keywords, patterns
            context_suggestions = self._get_context_suggestions()
            for suggestion in context_suggestions:
                if suggestion.name not in seen and suggestion.name.startswith(current_word):
                    suggestion.score = 800
                    suggestions.append(suggestion)
                    seen.add(suggestion.name)

            # Jedi completions - only for Python files and if not too many characters
            if self.current_file and str(self.current_file).endswith('.py') and len(self.text) < 50000:
                try:
                    script = Script(code=self.text, path=str(self.current_file))
                    row, column = self.cursor_location
                    jedi_completions = script.complete(row + 1, column)
                    
                    # Limit jedi results to avoid performance issues
                    for comp in jedi_completions[:20]:  # Max 20 jedi completions
                        if comp.name not in seen and comp.name.startswith(current_word):
                            comp.score = 500
                            suggestions.append(comp)
                            seen.add(comp.name)
                except Exception:
                    # Silently fail for jedi - it's not critical
                    pass

            # Local completions - cached and filtered
            local_completions = self._get_local_completions()
            for comp in local_completions:
                if comp.name not in seen and comp.name.startswith(current_word):
                    comp.score = 100
                    suggestions.append(comp)
                    seen.add(comp.name)

            # Sort by score and limit results
            suggestions.sort(key=lambda x: (-getattr(x, "score", 0), x.name.lower()))
            return suggestions[:15]  # Limit to 15 total suggestions

        except Exception as e:
            # For debugging - show the error temporarily
            self.notify(f"Completion error: {str(e)}", severity="error", timeout=2)
            return []

    def _score_suggestion(self, suggestion, current_word: str) -> float:
        name = suggestion.name.lower()
        current = current_word.lower()

        similarity = SequenceMatcher(None, current, name).ratio()
        score = similarity * 100

        if name.startswith(current):
            score += 20

        score += 1.0 / len(name)

        type_bonus = {
            "function": 2.0,
            "class": 2.0,
            "keyword": 3.0,
            "module": 1.5,
            "method": 1.5,
            "property": 1.0,
        }
        score += type_bonus.get(getattr(suggestion, "type", ""), 0.0)

        return score

    def _fuzzy_match(self, pattern: str, text: str) -> bool:
        """Simple fuzzy matching algorithm"""
        pattern = pattern.lower()
        text = text.lower()

        if not pattern or not text:
            return False

        pattern_idx = 0
        for char in text:
            if char == pattern[pattern_idx]:
                pattern_idx += 1
                if pattern_idx == len(pattern):
                    return True
        return False

    def _get_context_suggestions(self) -> list:
        row, col = self.cursor_location
        lines = self.text.split("\n")
        current_line = lines[row] if row < len(lines) else ""
        line_before_cursor = current_line[:col]

        suggestions = []

        current_word, _ = self._get_current_word()
        
        # Decorators
        if current_word.startswith("@"):
            decorators = [
                ("@classmethod", "decorator", "Class method decorator"),
                ("@staticmethod", "decorator", "Static method decorator"),
                ("@property", "decorator", "Property decorator"),
                ("@dataclass", "decorator", "Data class decorator"),
            ]
            for name, type_, desc in decorators:
                suggestions.append(self._create_completion(name, type_, desc))
            return suggestions

        # Import context
        if line_before_cursor.strip().startswith(("import", "from")):
            for module, desc in self._common_imports.items():
                suggestions.append(self._create_completion(module, "module", desc))
            return suggestions

        # Add common patterns if at start of line or after indentation
        stripped_line = line_before_cursor.strip()
        if stripped_line == "" or stripped_line.isspace():
            for pattern, (type_, desc) in self._common_patterns.items():
                suggestions.append(self._create_completion(pattern, type_, desc))

        return suggestions

    def _create_completion(
        self, name: str, type_: str, description: str
    ) -> "_LocalCompletion":
        completion = self._LocalCompletion(name)
        completion.type = type_
        completion.description = description
        return completion

    def action_show_completions(self) -> None:
        completions = self._get_completions()
        if not completions:
            self.notify("No completions available", severity="info", timeout=1)
            return

        # Hide existing popup if any
        if self._completion_popup:
            self.hide_completions()

        popup = AutoCompletePopup()
        popup.populate(completions)

        row, col = self.cursor_location
        popup.styles.offset = (col, row + 1)

        self._completion_popup = popup
        self.mount(popup)

        popup.focus()

    def hide_completions(self) -> None:
        if self._completion_popup:
            self._completion_popup.remove()
            self._completion_popup = None

    def on_auto_complete_popup_selected(
        self, message: AutoCompletePopup.Selected
    ) -> None:
        if message.value:
            lines = self.text.split("\n")
            row, col = self.cursor_location
            current_word, word_start = self._get_current_word()
            line = lines[row]
            lines[row] = line[:word_start] + message.value + line[col:]
            self.text = "\n".join(lines)
            new_cursor_col = word_start + len(message.value)
            self._move_cursor_preserve_scroll((row, new_cursor_col))

        self.hide_completions()
        self.focus()
        
        # Ensure we stay in insert mode if we were already there
        if self.mode == "insert":
            self.status_bar.update_mode("INSERT")
            self.cursor_blink = True

    def execute_command(self) -> None:
        command = self.command[1:].strip()

        # Handle line number jumps (e.g., :42)
        if command.isdigit():
            line_num = int(command) - 1  # Convert to 0-based
            lines = self.text.split("\n")
            if 0 <= line_num < len(lines):
                self._move_cursor_preserve_scroll((line_num, 0))
            else:
                self.notify(f"Line {command} out of range", severity="warning")
            return

        if command == "w":
            self.action_save_file()
        elif command == "wq":
            if not self.current_file:
                self.notify("No file name", severity="error")
                return
            self.action_save_file()
            if self.tabs:
                self.close_current_tab()
            else:
                self.clear_editor()
        elif command == "q":
            if self._modified:
                self.notify(
                    "No write since last change (add ! to override)", severity="warning"
                )
                return
            if self.tabs:
                self.close_current_tab()
            else:
                self.clear_editor()
        elif command == "q!":
            if self.tabs:
                self.close_current_tab()
            else:
                self.clear_editor()
        elif command == "x" or command == "wq":
            # Save and quit
            if self._modified and self.current_file:
                self.action_save_file()
            if self.tabs:
                self.close_current_tab()
            else:
                self.clear_editor()
        elif command == "%d":
            self.clear_editor()
        elif command in ["n", "bn"]:
            if self.tabs:
                # Save current buffer state before switching
                self._save_buffer_state()
                
                self.active_tab_index = (self.active_tab_index + 1) % len(self.tabs)
                tab = self.tabs[self.active_tab_index]
                self.load_text(tab.content)
                self.current_file = tab.path
                self._modified = tab.modified
                self.set_language_from_file(str(tab.path))
                
                # Restore buffer state
                self._restore_buffer_state()
                self._update_status_info()
        elif command in ["p", "bp", "prev"]:
            if self.tabs:
                # Save current buffer state before switching
                self._save_buffer_state()
                
                self.active_tab_index = (self.active_tab_index - 1) % len(self.tabs)
                tab = self.tabs[self.active_tab_index]
                self.load_text(tab.content)
                self.current_file = tab.path
                self._modified = tab.modified
                self.set_language_from_file(str(tab.path))
                
                # Restore buffer state
                self._restore_buffer_state()
                self._update_status_info()
        elif command in ["ls", "buffers"]:
            buffer_list = []
            for i, tab in enumerate(self.tabs):
                marker = "%" if i == self.active_tab_index else " "
                modified = "+" if tab.modified else " "
                name = os.path.basename(tab.path)
                buffer_list.append(f"{i + 1}{marker}{modified} {name}")
            self.notify("\n".join(buffer_list) if buffer_list else "No buffers")
        elif command.startswith("e "):
            # Edit file - :e filename
            filename = command[2:].strip()
            if filename:
                try:
                    self.open_file(filename)
                except Exception as e:
                    self.notify(f"Cannot edit {filename}: {str(e)}", severity="error")
        elif command == "set number" or command == "set nu":
            self.show_line_numbers = True
        elif command == "set nonumber" or command == "set nonu":
            self.show_line_numbers = False
        else:
            self.notify(f"Unknown command: :{command}", severity="warning")

    def close_current_tab(self) -> None:
        if not self.tabs:
            return

        self.tabs.pop(self.active_tab_index)
        if self.tabs:
            self.active_tab_index = max(
                0, min(self.active_tab_index, len(self.tabs) - 1)
            )
            tab = self.tabs[self.active_tab_index]
            self.load_text(tab.content)
            self.current_file = tab.path
            self._modified = tab.modified
            
            # Restore buffer state
            self._restore_buffer_state()
        else:
            self.active_tab_index = -1
            self.load_text("")
            self.current_file = None
            self._modified = False
        self._update_status_info()

    def render(self) -> str:
        content = str(super().render())

        if self.in_command_mode:
            content += f"\nCommand: {self.command}"

        return content

    def set_language_from_file(self, filepath: str) -> None:
        ext = os.path.splitext(filepath)[1].lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".html": "html",
            ".css": "css",
            ".md": "markdown",
            ".json": "json",
            ".sh": "bash",
            ".sql": "sql",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".xml": "xml",
            ".txt": None,
        }

        self.language = language_map.get(ext)
        if self.language:
            try:
                self._syntax = Syntax(
                    self.text,
                    self.language,
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=False,
                    indent_guides=True,
                )
                self.update_syntax_highlighting()
            except Exception as e:
                self.notify(f"Syntax highlighting error: {e}", severity="error")

    def update_syntax_highlighting(self) -> None:
        if self.language and self.text and self._syntax:
            try:
                self._syntax.code = self.text
                rich_text = Text.from_ansi(str(self._syntax))
                self.highlight_text = rich_text
            except (SyntaxError, ValueError) as e:
                self.notify(f"Highlighting update error: {e}", severity="error")

    def clear_editor(self) -> None:
        self.text = ""
        if self.command == "%d":
            self.notify("Editor Cleared", severity="info")
        self.refresh()

    def action_write(self) -> None:
        if not self.current_file:
            self.notify("No file to save", severity="warning")
            return

        self.action_save_file()

    def action_write_quit(self) -> None:
        if not self.current_file:
            self.notify("No file to save", severity="warning")
            return

        self.action_save_file()
        if self.tabs:
            self.close_current_tab()
        else:
            self.clear_editor()

    def action_quit(self) -> None:
        if self._modified:
            self.notify(
                "No write since last change (add ! to override)", severity="warning"
            )
            return

        if self.tabs:
            self.close_current_tab()
        else:
            self.clear_editor()

    def action_force_quit(self) -> None:
        if self.tabs:
            self.close_current_tab()
        else:
            self.clear_editor()

    def action_indent(self) -> None:
        cursor_location = self.cursor_location
        self.insert(" " * self.tab_size)
        new_location = (cursor_location[0], cursor_location[1] + self.tab_size)
        self.move_cursor(new_location)

    def action_unindent(self) -> None:
        cursor_location = self.cursor_location
        lines = self.text.split("\n")
        current_line = lines[cursor_location[0]] if lines else ""

        if current_line.startswith(" " * self.tab_size):
            self.move_cursor((cursor_location[0], 0))
            for _ in range(self.tab_size):
                self.action_delete_left()

    def action_save_file(self) -> None:
        if self.current_file:
            try:
                with open(str(self.current_file), "w", encoding="utf-8") as file:
                    file.write(self.text)
                self._modified = False
                self.post_message(self.FileModified(False))
                saved_size = os.path.getsize(str(self.current_file))
                self.notify(
                    f"Wrote {saved_size} bytes to {os.path.basename(str(self.current_file))}"
                )
                self._update_status_info()
            except (IOError, OSError) as e:
                self.notify(f"Error saving file: {e}", severity="error")

    def watch_text(self, old_text: str, new_text: str) -> None:
        if old_text != new_text:
            # Invalidate completion cache when text changes
            self._text_changed_since_cache = True
            
            # Save undo state for the current buffer (only if not undoing/redoing)
            if not self._is_undoing:
                self._save_undo_state(old_text)

            self._modified = True
            self.post_message(self.FileModified(True))

            # Update current tab content and state
            if self.tabs and self.active_tab_index >= 0:
                tab = self.tabs[self.active_tab_index]
                tab.content = new_text
                tab.modified = True
                # Update saved position
                tab.cursor_position = self.cursor_location
                tab.scroll_position = self.scroll_offset

            if self._syntax:
                self.update_syntax_highlighting()
            self._update_status_info()

    def action_enter_normal_mode(self) -> None:
        self.mode = "normal"
        self._visual_start = None
        self._visual_mode = None
        self._clear_vim_state()
        self.status_bar.update_mode("NORMAL")
        self.cursor_blink = False
        self.hide_completions()

    def action_enter_insert_mode(self) -> None:
        self.mode = "insert"
        self.status_bar.update_mode("INSERT")
        self.cursor_blink = True

    def action_move_left(self) -> None:
        if self.mode == "normal":
            self.move_cursor_relative(-1, 0)

    def action_move_right(self) -> None:
        if self.mode == "normal":
            self.move_cursor_relative(1, 0)

    def action_move_down(self) -> None:
        if self.mode == "normal":
            self.move_cursor_relative(0, 1)

    def action_move_up(self) -> None:
        if self.mode == "normal":
            self.move_cursor_relative(0, -1)

    def action_move_word_forward(self) -> None:
        if self.mode == "normal":
            current_scroll = self.scroll_offset
            lines = self.text.split("\n")
            cur_row, cur_col = self.cursor_location
            line = lines[cur_row] if cur_row < len(lines) else ""
            while cur_col < len(line) and line[cur_col].isspace():
                cur_col += 1
            while cur_col < len(line) and not line[cur_col].isspace():
                cur_col += 1
            self.move_cursor((cur_row, cur_col))
            self.scroll_to(current_scroll[0], current_scroll[1], animate=False)

    def action_move_word_backward(self) -> None:
        if self.mode == "normal":
            current_scroll = self.scroll_offset
            lines = self.text.split("\n")
            cur_row, cur_col = self.cursor_location
            line = lines[cur_row] if cur_row < len(lines) else ""
            while cur_col > 0 and line[cur_col - 1].isspace():
                cur_col -= 1
            while cur_col > 0 and not line[cur_col - 1].isspace():
                cur_col -= 1
            self.move_cursor((cur_row, cur_col))
            self.scroll_to(current_scroll[0], current_scroll[1], animate=False)

    def action_move_line_start(self) -> None:
        if self.mode == "normal":
            current_scroll = self.scroll_offset
            self.move_cursor((self.cursor_location[0], 0))
            self.scroll_to(current_scroll[0], current_scroll[1], animate=False)

    def action_undo(self) -> None:
        """Undo the last change in the current buffer."""
        if self.mode == "normal" and self.tabs and self.active_tab_index >= 0:
            tab = self.tabs[self.active_tab_index]
            
            if not tab.undo_stack:
                self.notify("Already at oldest change", severity="info")
                return
                
            self._is_undoing = True

            # Save current state to redo stack
            current_state = {
                "text": self.text,
                "cursor": self.cursor_location,
                "scroll": self.scroll_offset,
            }
            tab.redo_stack.append(current_state)

            # Get state from undo stack
            state = tab.undo_stack.pop()

            # Restore text
            self.text = state["text"]
            tab.content = state["text"]
            tab.modified = True

            # Restore cursor position and scroll offset
            self.move_cursor(state["cursor"])
            self.scroll_to(state["scroll"][0], state["scroll"][1], animate=False)
            
            # Update tab's saved position
            tab.cursor_position = state["cursor"]
            tab.scroll_position = state["scroll"]

            self._is_undoing = False
            self._update_status_info()

    def action_redo(self) -> None:
        """Redo the last undone change in the current buffer."""
        if self.mode == "normal" and self.tabs and self.active_tab_index >= 0:
            tab = self.tabs[self.active_tab_index]
            
            if not tab.redo_stack:
                self.notify("Already at newest change", severity="info")
                return
                
            self._is_undoing = True

            # Save current state to undo stack
            current_state = {
                "text": self.text,
                "cursor": self.cursor_location,
                "scroll": self.scroll_offset,
            }
            tab.undo_stack.append(current_state)

            # Get state from redo stack
            state = tab.redo_stack.pop()

            # Restore text
            self.text = state["text"]
            tab.content = state["text"]
            tab.modified = True

            # Restore cursor position and scroll offset
            self.move_cursor(state["cursor"])
            self.scroll_to(state["scroll"][0], state["scroll"][1], animate=False)
            
            # Update tab's saved position
            tab.cursor_position = state["cursor"]
            tab.scroll_position = state["scroll"]

            self._is_undoing = False
            self._update_status_info()

    def action_move_line_end(self) -> None:
        if self.mode == "normal":
            current_scroll = self.scroll_offset
            lines = self.text.split("\n")
            cur_row = self.cursor_location[0]
            if cur_row < len(lines):
                line_length = len(lines[cur_row])
                self.move_cursor((cur_row, line_length))
            self.scroll_to(current_scroll[0], current_scroll[1], animate=False)

    def action_move_line_first_char(self) -> None:
        """Move to first non-blank character of line (^ command)."""
        current_scroll = self.scroll_offset
        lines = self.text.split("\n")
        cur_row = self.cursor_location[0]
        if cur_row < len(lines):
            line = lines[cur_row]
            col = 0
            while col < len(line) and line[col].isspace():
                col += 1
            self.move_cursor((cur_row, col))
        self.scroll_to(current_scroll[0], current_scroll[1], animate=False)

    def action_vim_g_commands(self) -> None:
        """Handle g-prefix commands in vim."""
        # This is handled in the key handler - g followed by g
        pass

    async def action_new_file(self) -> None:
        try:
            tree = self.app.screen.query_one(FilterableDirectoryTree)
            current_path = tree.path if tree.path else os.path.expanduser("~")
        except Exception:
            current_path = os.path.expanduser("~")

        dialog = NewFileDialog(current_path)
        await self.app.push_screen(dialog)

    def open_file(self, filepath: str) -> None:
        try:
            # Save current buffer state before switching
            if self.tabs and self.active_tab_index >= 0:
                self._save_buffer_state()
            
            # Check if file is already open
            for i, tab in enumerate(self.tabs):
                if tab.path == filepath:
                    self.active_tab_index = i
                    self.load_text(tab.content)
                    self.current_file = tab.path
                    self._modified = tab.modified
                    self.set_language_from_file(str(filepath))
                    
                    # Restore buffer state
                    self._restore_buffer_state()
                    self._update_status_info()
                    return

            # Open new file
            with open(filepath, "r", encoding="utf-8") as file:
                content = file.read()
                new_tab = EditorTab(filepath, content)
                self.tabs.append(new_tab)
                self.active_tab_index = len(self.tabs) - 1

                self.load_text(content)
                self.current_file = filepath
                self.set_language_from_file(str(filepath))
                self._modified = False
                self.mode = "normal"
                self.status_bar.update_mode("NORMAL")
                self.cursor_blink = False
                
                # Reset cursor and scroll for new file
                self.move_cursor((0, 0))
                self.scroll_to(0, 0, animate=False)
                
                self.focus()
                self._update_status_info()
        except Exception as e:
            self.notify(f"Error opening file: {str(e)}", severity="error")


class NestView(Container, InitialFocusMixin):
    BINDINGS = [
        Binding("ctrl+h", "toggle_hidden", "Toggle Hidden Files", show=True),
        Binding("ctrl+b", "toggle_sidebar", "Toggle Sidebar", show=True),
        Binding("ctrl+right", "focus_editor", "Focus Editor", show=True),
        Binding("r", "refresh_tree", "Refresh Tree", show=True),
        Binding("ctrl+n", "new_file", "New File", show=True),
        Binding("ctrl+shift+n", "new_folder", "New Folder", show=True),
        Binding("d", "delete_selected", "Delete Selected", show=True),
        Binding("ctrl+v", "paste", "Paste", show=True),
        Binding("shift+/", "ContextMenu", "ContextMenu", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.show_hidden = False
        self.show_sidebar = True
        self.editor = None

    async def action_new_file(self) -> None:
        editor = self.query_one(CodeEditor)
        await editor.action_new_file()

    async def action_new_folder(self) -> None:
        try:
            tree = self.query_one(FilterableDirectoryTree)
            current_path = tree.path if tree.path else os.path.expanduser("~")
        except Exception:
            current_path = os.path.expanduser("~")

        dialog = NewFolderDialog(current_path)
        await self.app.push_screen(dialog)

    async def action_delete_selected(self) -> None:
        if self.app.focused is self.query_one(FilterableDirectoryTree):
            tree = self.query_one(FilterableDirectoryTree)
            await tree.action_delete_selected()

    def on_file_created(self, event: FileCreated) -> None:
        self.notify(f"Created file: {os.path.basename(event.path)}")
        tree = self.query_one(FilterableDirectoryTree)
        tree.refresh_tree()

    def on_folder_created(self, event: FolderCreated) -> None:
        self.notify(f"Created folder: {os.path.basename(event.path)}")
        tree = self.query_one(FilterableDirectoryTree)
        tree.refresh_tree()

    def on_file_deleted(self, event: FileDeleted) -> None:
        editor = self.query_one(CodeEditor)
        tabs_to_remove = []

        for i, tab in enumerate(editor.tabs):
            if tab.path == event.path or tab.path.startswith(event.path + os.sep):
                tabs_to_remove.append(i)

        for i in sorted(tabs_to_remove, reverse=True):
            if i == editor.active_tab_index:
                editor.close_current_tab()
            else:
                editor.tabs.pop(i)
                if i < editor.active_tab_index:
                    editor.active_tab_index -= 1

        editor._update_status_info()

    def compose(self) -> ComposeResult:
        yield Container(
            Horizontal(
                Container(
                    Horizontal(
                        Static("Files", classes="nav-title"),
                        Button(
                            "-",
                            id="toggle_hidden",
                            variant="default",
                            classes="toggle-hidden-btn",
                        ),
                        Button(
                            "New File",
                            id="new_file",
                            variant="default",
                            classes="new-file-btn",
                        ),
                        Button(
                            "New Folder",
                            id="new_folder",
                            variant="default",
                            classes="new-file-btn",
                        ),
                        classes="nav-header",
                    ),
                    FilterableDirectoryTree(
                        os.path.expanduser("~"),
                        show_hidden=self.show_hidden,
                        id="main_tree",
                    ),
                    classes="file-nav",
                ),
                Container(CustomCodeEditor(), classes="editor-container"),
                classes="main-container",
            ),
            id="nest-view",
        )

    def on_mount(self) -> None:
        self.editor = self.query_one(CodeEditor)
        tree = self.query_one("#main_tree", FilterableDirectoryTree)
        tree.focus()

        self.app.main_tree = tree

        self.editor.can_focus_tab = True
        self.editor.key_handlers = {
            "ctrl+left": lambda: self.action_focus_tree(),
            "ctrl+n": self.action_new_file,
            "ctrl+shift+n": self.action_new_folder,
        }

        tree.key_handlers = {
            "ctrl+n": self.action_new_file,
            "ctrl+shift+n": self.action_new_folder,
        }

    def action_toggle_hidden(self) -> None:
        self.show_hidden = not self.show_hidden
        tree = self.query_one(FilterableDirectoryTree)
        tree.show_hidden = self.show_hidden
        tree.reload()

        toggle_btn = self.query_one("#toggle_hidden")
        toggle_btn.label = "+" if self.show_hidden else "-"
        self.notify("Hidden files " + ("shown" if self.show_hidden else "hidden"))

    def action_toggle_sidebar(self) -> None:
        self.show_sidebar = not self.show_sidebar
        file_nav = self.query_one(".file-nav")
        if not self.show_sidebar:
            file_nav.add_class("hidden")
            if self.app.focused is self.query_one(FilterableDirectoryTree):
                self.query_one(CodeEditor).focus()
        else:
            file_nav.remove_class("hidden")

    def action_focus_editor(self) -> None:
        self.query_one(CodeEditor).focus()

    def action_focus_tree(self) -> None:
        self.query_one(FilterableDirectoryTree).focus()

    def action_refresh_tree(self) -> None:
        tree = self.query_one(FilterableDirectoryTree)
        tree.refresh_tree()
        self.notify("Tree refreshed")

    async def action_paste(self) -> None:
        """Paste a file or directory from the clipboard."""
        if not hasattr(self.app, "file_clipboard") or not self.app.file_clipboard:
            self.notify("Nothing to paste", severity="warning")
            return

        clipboard = self.app.file_clipboard
        source_path = clipboard.get("path")
        action = clipboard.get("action")

        if not source_path or not os.path.exists(source_path):
            self.notify("Source no longer exists", severity="error")
            self.app.file_clipboard = None
            return

        tree = self.query_one(FilterableDirectoryTree)
        if tree.cursor_node and os.path.isdir(tree.cursor_node.data.path):
            dest_dir = tree.cursor_node.data.path
        else:
            dest_dir = tree.path

        basename = os.path.basename(source_path)
        dest_path = os.path.join(dest_dir, basename)

        if os.path.exists(dest_path):
            self.notify(f"'{basename}' already exists in destination", severity="error")
            return

        try:
            if action == "copy":
                if os.path.isdir(source_path):
                    shutil.copytree(source_path, dest_path)
                    self.notify(f"Copied folder: {basename}")
                else:
                    shutil.copy2(source_path, dest_path)
                    self.notify(f"Copied file: {basename}")
            elif action == "cut":
                shutil.move(source_path, dest_path)
                self.notify(f"Moved: {basename}")
                self.app.file_clipboard = None

                editor = self.app.query_one(CodeEditor)
                for i, tab in enumerate(editor.tabs):
                    if tab.path == source_path:
                        tab.path = dest_path
                        if i == editor.active_tab_index:
                            editor.current_file = dest_path
                        editor._update_status_info()

            tree.refresh_tree()

        except Exception as e:
            self.notify(f"Error during paste operation: {str(e)}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "toggle_hidden":
            self.action_toggle_hidden()
            event.stop()
        elif event.button.id == "new_file":
            self.run_worker(self.action_new_file())
            event.stop()
        elif event.button.id == "new_folder":
            self.run_worker(self.action_new_folder())
            event.stop()
        elif event.button.id == "refresh_tree":
            self.action_refresh_tree()
            event.stop()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        try:
            # First check if it's a Python file by extension - this is a quick check to avoid binary detection, will implenent
            # a more robust solution later
            if str(event.path).endswith(".py"):
                editor = self.query_one(CodeEditor)
                editor.open_file(event.path)
                editor.focus()
                event.stop()
                return

            # For non-Python files, do binary detection
            with open(event.path, "rb") as file:
                # Read first chunk
                chunk = file.read(8192)

                binary_signatures = [
                    b"\x7fELF",
                    b"MZ",
                    b"\x89PNG",
                    b"\xff\xd8\xff",
                    b"GIF",
                    b"BM",
                    b"PK",
                    b"\x1f\x8b",
                ]

                if any(chunk.startswith(sig) for sig in binary_signatures):
                    self.notify("Cannot open binary file", severity="warning")
                    event.stop()
                    return

                if b"\x00" in chunk:
                    self.notify("Cannot open binary file", severity="warning")
                    event.stop()
                    return

                try:
                    chunk.decode("utf-8")
                    editor = self.query_one(CodeEditor)
                    editor.open_file(event.path)
                    editor.focus()
                    event.stop()
                except UnicodeDecodeError:
                    self.notify(
                        "Cannot open file: Not a valid UTF-8 text file",
                        severity="warning",
                    )
                    event.stop()

        except (IOError, OSError) as e:
            self.notify(f"Error opening file: {str(e)}", severity="error")
            event.stop()

    def get_initial_focus(self) -> Optional[Widget]:
        return self.query_one(FilterableDirectoryTree)


class CustomCodeEditor(CodeEditor):
    BINDINGS = [
        *CodeEditor.BINDINGS,
        Binding("shift+left", "focus_tree", "Focus Tree", show=True),
        Binding("ctrl+shift+n", "new_folder", "New Folder", show=True),
    ]

    def action_focus_tree(self) -> None:
        self.app.query_one("NestView").action_focus_tree()

    async def action_new_folder(self) -> None:
        await self.app.query_one("NestView").action_new_folder()

    # Add missing action methods that are referenced in the CodeEditor's on_key method
    def action_delete_char(self) -> None:
        # Call the parent class method
        super().action_delete_char()

    def action_delete_line(self) -> None:
        # Call the parent class method
        super().action_delete_line()

    def action_delete_to_end(self) -> None:
        # Call the parent class method
        super().action_delete_to_end()


class ContextMenu(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("up", "focus_previous", "Previous Item"),
        Binding("down", "focus_next", "Next Item"),
        Binding("enter", "select_focused", "Select Item"),
    ]

    def __init__(self, items: list[tuple[str, str]], x: int, y: int, path: str) -> None:
        super().__init__()
        self.items = items
        self.pos_x = x
        self.pos_y = y
        self.path = path
        self.current_focus_index = 0

    def compose(self) -> ComposeResult:
        with Container(classes="context-menu-container"):
            with Vertical(classes="file-form", id="menu-container"):
                yield Static("Actions", classes="file-form-header")

                for item_label, item_action in self.items:
                    yield Button(
                        item_label,
                        id=f"action-{item_action}",
                        classes="context-menu-item",
                    )

    def on_mount(self) -> None:
        menu = self.query_one(".context-menu-container")

        # Get the tree widget to position the menu relative to it
        try:
            tree = self.app.query_one("#main_tree", FilterableDirectoryTree)
            tree_region = tree.region
        except Exception:
            tree_region = None

        if hasattr(self, 'pos_x') and hasattr(self, 'pos_y'):
            # For right-click events, position near the click but ensure it's within the tree area
            menu_x = self.pos_x
            menu_y = self.pos_y
            
            if tree_region:
                # Ensure the menu appears within or near the tree sidebar
                # Add a small offset so it doesn't cover the clicked item
                menu_x = max(tree_region.x + 5, min(menu_x + 5, tree_region.x + tree_region.width - 160))
                menu_y = max(tree_region.y + 5, min(menu_y, tree_region.y + tree_region.height - 200))
            else:
                # Fallback bounds checking
                menu_x = max(5, min(menu_x + 5, self.app.screen.size.width - 160))
                menu_y = max(5, min(menu_y, self.app.screen.size.height - 200))
                
            menu.styles.offset = (menu_x, menu_y)

        if self.items:
            buttons = self.query(Button)
            if buttons:
                buttons.first().focus()
                self.current_focus_index = 0

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self._handle_action(event.button.id)

    def action_focus_next(self) -> None:
        buttons = list(self.query(Button))
        if not buttons:
            return

        self.current_focus_index = (self.current_focus_index + 1) % len(buttons)
        buttons[self.current_focus_index].focus()

    def action_focus_previous(self) -> None:
        buttons = list(self.query(Button))
        if not buttons:
            return

        self.current_focus_index = (self.current_focus_index - 1) % len(buttons)
        buttons[self.current_focus_index].focus()

    def action_select_focused(self) -> None:
        focused = self.app.focused
        if isinstance(focused, Button):
            self._handle_action(focused.id)

    def action_cancel(self) -> None:
        self.dismiss()

    def _handle_action(self, button_id) -> None:
        if (
            not button_id
            or not isinstance(button_id, str)
            or not button_id.startswith("action-")
        ):
            self.dismiss()
            return

        action = button_id.replace("action-", "")

        if action == "delete":
            self.dismiss()
            dialog = DeleteConfirmationDialog(self.path)
            self.app.push_screen(dialog)
        elif action == "rename":
            self.dismiss()
            dialog = RenameDialog(self.path)
            self.app.push_screen(dialog)
        elif action == "new_file":
            self.dismiss()
            if os.path.isdir(self.path):
                dialog = NewFileDialog(self.path)
                self.app.push_screen(dialog)
        elif action == "new_folder":
            self.dismiss()
            if os.path.isdir(self.path):
                dialog = NewFolderDialog(self.path)
                self.app.push_screen(dialog)
        elif action == "copy":
            self.app.file_clipboard = {"action": "copy", "path": self.path}
            self.app.notify(f"Copied: {os.path.basename(self.path)}")
            self.dismiss()
        elif action == "cut":
            self.app.file_clipboard = {"action": "cut", "path": self.path}
            self.app.notify(f"Cut: {os.path.basename(self.path)}")
            self.dismiss()
        else:
            self.dismiss()

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            self.dismiss()
            event.prevent_default()
            event.stop()
        elif event.key == "up":
            self.action_focus_previous()
            event.prevent_default()
            event.stop()
        elif event.key == "down":
            self.action_focus_next()
            event.prevent_default()
            event.stop()
        elif event.key == "enter":
            self.action_select_focused()
            event.prevent_default()
            event.stop()


class RenameDialog(ModalScreen):
    """Dialog for renaming files and directories."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "submit", "Submit"),
    ]

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path
        self.old_name = os.path.basename(path)
        self.parent_dir = os.path.dirname(path)

    def compose(self) -> ComposeResult:
        with Container(classes="file-form-container"):
            with Vertical(classes="file-form"):
                item_type = "Folder" if os.path.isdir(self.path) else "File"
                yield Static(f"Rename {item_type}", classes="file-form-header")

                with Vertical():
                    yield Label("Current name:")
                    yield Static(self.old_name, id="current-name")

                with Vertical():
                    yield Label("New name:")
                    yield Input(value=self.old_name, id="new-name")

                with Horizontal(classes="form-buttons"):
                    yield Button("Cancel", variant="error", id="cancel")
                    yield Button("Rename", variant="success", id="submit")

    def on_mount(self) -> None:
        self.query_one("#new-name").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
        elif event.button.id == "submit":
            self._handle_rename()

    def _handle_rename(self) -> None:
        new_name = self.query_one("#new-name").value

        if not new_name:
            self.notify("Name cannot be empty", severity="error")
            return

        if new_name == self.old_name:
            self.dismiss(False)
            return

        new_path = os.path.join(self.parent_dir, new_name)

        if os.path.exists(new_path):
            self.notify(f"'{new_name}' already exists", severity="error")
            return

        try:
            os.rename(self.path, new_path)

            if hasattr(self.app, "main_tree") and self.app.main_tree:
                self.app.main_tree.refresh_tree()

            editor = self.app.query_one(CodeEditor)
            for i, tab in enumerate(editor.tabs):
                if tab.path == self.path:
                    tab.path = new_path
                    if i == editor.active_tab_index:
                        editor.current_file = new_path
                    editor._update_status_info()

            self.notify(f"Renamed to: {new_name}")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error renaming: {str(e)}", severity="error")
            self.dismiss(False)

    async def action_submit(self) -> None:
        self._handle_rename()

    async def action_cancel(self) -> None:
        self.dismiss(False)
