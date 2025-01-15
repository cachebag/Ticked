from textual.app import ComposeResult
from textual.widget import Widget
from textual.containers import Horizontal, Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import DirectoryTree, Static, Button, TextArea, Input, Label
from textual.binding import Binding
from ...ui.mixins.focus_mixin import InitialFocusMixin
from typing import Optional
from textual.message import Message
from rich.syntax import Syntax
from rich.text import Text
import os

class EditorTab:
    def __init__(self, path: str, content: str):
        self.path = path
        self.content = content
        self.modified = False

class FileCreated(Message):
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path

class FilterableDirectoryTree(DirectoryTree):
    def __init__(self, path: str, show_hidden: bool = False) -> None:
        super().__init__(path)
        self.show_hidden = show_hidden

    def filter_paths(self, paths: list[str]) -> list[str]:
        if self.show_hidden:
            return paths
        return [path for path in paths if not os.path.basename(path).startswith('.')]

    def refresh_tree(self) -> None:
        self.path = self.path
        self.reload()
        self.refresh(layout=True)

class NewFileDialog(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("f1", "submit", "Submit"),
        Binding("tab", "next_field", "Next Field")
    ]

    def __init__(self, initial_path: str) -> None:
        super().__init__()
        self.selected_path = initial_path

    def compose(self) -> ComposeResult:
        with Container(classes="task-form-container"):
            with Vertical(classes="task-form"):
                yield Static("Create New File", classes="form-header")
                
                with Vertical():
                    yield Label("Selected Directory:")
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

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
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
            with open(full_path, 'w') as f:
                f.write("")
            self.dismiss(full_path)
            self.app.post_message(FileCreated(full_path))
            tree = self.app.query_one(FilterableDirectoryTree)
            tree.refresh_tree()
            editor = self.app.query_one(CodeEditor)
            # open the file as soon as it's created
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
        parts = []
        
        mode_style = {
            "NORMAL": "cyan",
            "INSERT": "green",
            "COMMAND": "yellow"
        }
        mode_color = mode_style.get(self.mode, "white")
        parts.append(f"[{mode_color}]{self.mode}[/]")
        
        if self.file_info:
            parts.append(self.file_info)
            
        if self.command:
            parts.append(f"[yellow]{self.command}[/]")
            
        self.update(" ".join(parts))

class CodeEditor(TextArea):
    BINDINGS = [
        Binding("ctrl+n", "new_file", "New File", show=True),
        Binding("tab", "indent", "Indent", show=False),
        Binding("shift+tab", "unindent", "Unindent", show=False),
        Binding("ctrl+]", "indent", "Indent", show=False),
        Binding("ctrl+[", "unindent", "Unindent", show=False),
        Binding("ctrl+s", "save_file", "Save File", show=True),
        Binding("escape", "enter_normal_mode", "Enter Normal Mode", show=False),
        Binding("i", "enter_insert_mode", "Enter Insert Mode", show=False),
        Binding("h", "move_left", "Move Left", show=False),
        Binding("l", "move_right", "Move Right", show=False),
        Binding("j", "move_down", "Move Down", show=False),
        Binding("k", "move_up", "Move Up", show=False),
        Binding("w", "move_word_forward", "Move Word Forward", show=False),
        Binding("b", "move_word_backward", "Move Word Backward", show=False),
        Binding("0", "move_line_start", "Move to Line Start", show=False),
        Binding("$", "move_line_end", "Move to Line End", show=False),
        Binding("shift+left", "focus_tree", "Focus Tree", show=True),
        Binding("u", "undo", "Undo", show=False),
        Binding("ctrl+r", "redo", "Redo", show=False),
        Binding(":w", "write", "Write", show=False),
        Binding(":wq", "write_quit", "Write and Quit", show=False),
        Binding(":q", "quit", "Quit", show=False),
        Binding(":q!", "force_quit", "Force Quit", show=False),
        Binding("%d", "clear_editor", "Clear Editor", show=False), 
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
        self.mode = "insert"
        self._undo_stack = []
        self._redo_stack = []
        self._last_text = ""
        self._is_undoing = False
        self.command = ""
        self.in_command_mode = False
        self.pending_command = ""
        self.status_bar = StatusBar()
        self.status_bar.update_mode("NORMAL")
        self.tabs = []
        self.active_tab_index = -1  

    def on_focus(self) -> None:
        self.mode = "normal"
        self.status_bar.update_mode("NORMAL")
        self.cursor_blink = False

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
            file_info.append(os.path.basename(self.current_file))
        if self._modified:
            file_info.append("[red][+][/]")
        if self.text:
            lines = len(self.text.split('\n'))
            chars = len(self.text)
            file_info.append(f"{lines}L, {chars}B")
        
        self.status_bar.update_file_info(" ".join(file_info))

    def on_key(self, event) -> None:
        if self.in_command_mode:
            if event.key == "enter":
                self.execute_command()
                self.in_command_mode = False
                self.command = ""
                self.refresh()
                event.prevent_default()
                event.stop()
            elif event.key == "escape":
                self.in_command_mode = False
                self.command = ""
                self.refresh()
                event.prevent_default()
                event.stop()
            elif event.is_printable:
                self.command += event.character
                self.refresh()
                event.prevent_default()
                event.stop()
            elif event.key == "backspace" and len(self.command) > 1:
                self.command = self.command[:-1]
                self.refresh()
                event.prevent_default()
                event.stop()
            self.status_bar.update_mode("COMMAND")
            self.status_bar.update_command(self.command)
        else:
            if self.mode == "insert":
                if event.is_printable:
                    self.cursor_type = "line"
                    self._save_undo_state()  
                    self.insert(event.character)
                    self._modified = True
                    self.post_message(self.FileModified(True))
                    event.prevent_default()
                    event.stop()
                elif event.key == "backspace":
                    self._save_undo_state()  
                    self.action_delete_left()
                    self._modified = True
                    self.post_message(self.FileModified(True))
                    event.prevent_default()
                    event.stop()
                elif event.key in ["left", "right", "up", "down"]:
                    return
            elif self.mode == "normal":
                if event.key == "u":
                    self.action_undo()
                    event.prevent_default()
                    event.stop()
                elif event.key == "ctrl+r":
                    self.action_redo()
                    event.prevent_default()
                    event.stop()
                motion_map = {
                    "h": self.action_move_left,
                    "l": self.action_move_right,
                    "j": self.action_move_down,
                    "k": self.action_move_up,
                    "w": self.action_move_word_forward,
                    "b": self.action_move_word_backward,
                    "0": self.action_move_line_start,
                    "$": self.action_move_line_end,
                    "x": self.action_delete_char,
                    "dd": self.action_delete_line,
                    "de": self.action_delete_to_end,
                }
            
                if self.pending_command and event.character:
                    combined_command = self.pending_command + event.character
                    if combined_command in motion_map:
                        motion_map[combined_command]()
                        self.pending_command = ""
                    else:
                        self.pending_command = "" 
                    event.prevent_default()
                    event.stop()
                elif event.character == "d":  
                    self.pending_command = "d"
                    event.prevent_default()
                    event.stop()
                elif event.character in motion_map:
                    motion_map[event.character]()
                    event.prevent_default()
                    event.stop()
                elif event.character == "i":
                    self.mode = "insert"
                    self.status_bar.update_mode("INSERT")
                    self.cursor_blink = True
                    event.prevent_default()
                    event.stop()
                elif event.character == ":":
                    self.in_command_mode = True
                    self.command = ":"
                    self.refresh()
                    event.prevent_default()
                    event.stop()
                elif event.key in ["left", "right", "up", "down"]:
                    return
                else:
                    if event.is_printable:
                        event.prevent_default()
                        event.stop()

    def execute_command(self) -> None:
        command = self.command[1:].strip()
        
        if command == "w":
            self.action_write()
            self.status_bar.update_mode("NORMAL")
            self.in_command_mode = False
            self.command = ""
            self.refresh()
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
                self.notify("No write since last change (add ! to override)", severity="warning")
                self.status_bar.update_mode("NORMAL")
                self.in_command_mode = False
                self.command = ""
                self.refresh()
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
        elif command == "%d":
            self.clear_editor()
        elif command == "n" or command == "bn":
            if self.tabs:
                self.active_tab_index = (self.active_tab_index + 1) % len(self.tabs)
                tab = self.tabs[self.active_tab_index]
                self.load_text(tab.content)
                self.current_file = tab.path
                self._update_status_info()
        elif command == "p" or command == "bp":
            if self.tabs:
                self.active_tab_index = (self.active_tab_index - 1) % len(self.tabs)
                tab = self.tabs[self.active_tab_index]
                self.load_text(tab.content)
                self.current_file = tab.path
                self._update_status_info()
        elif command == "ls":
            buffer_list = []
            for i, tab in enumerate(self.tabs):
                marker = "%" if i == self.active_tab_index else " "
                modified = "+" if tab.modified else " "
                name = os.path.basename(tab.path)
                buffer_list.append(f"{i + 1}{marker}{modified} {name}")
            self.notify("\n".join(buffer_list))
        else:
            self.notify(f"Unknown command: {command}", severity="warning")


    def close_current_tab(self) -> None:
        if not self.tabs:
            return
            
        self.tabs.pop(self.active_tab_index)
        if self.tabs:
            self.active_tab_index = max(0, min(self.active_tab_index, len(self.tabs) - 1))
            tab = self.tabs[self.active_tab_index]
            self.load_text(tab.content)
            self.current_file = tab.path
        else:
            self.active_tab_index = -1
            self.load_text("")
            self.current_file = None
        self._update_status_info()

    def render(self) -> str:
        content = str(super().render())
    
        if self.in_command_mode:
            content += f"\nCommand: {self.command}"
    
        return content

    def set_language_from_file(self, filepath: str) -> None:
        ext = os.path.splitext(filepath)[1].lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.html': 'html',
            '.css': 'css',
            '.md': 'markdown',
            '.json': 'json',
            '.sh': 'bash',
            '.sql': 'sql',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.xml': 'xml',
            '.txt': None
        }
        
        self.language = language_map.get(ext)
        if self.language:
            try:
                self._syntax = Syntax(
                    self.text,
                    self.language,
                    theme="dracula",
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
            self.notify("No write since last change (add ! to override)", severity="warning")
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
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(self.text)
                self._modified = False
                self.post_message(self.FileModified(False))
                saved_size = os.path.getsize(self.current_file)
                self.notify(f"Wrote {saved_size} bytes to {os.path.basename(self.current_file)}")
                self._update_status_info()
            except (IOError, OSError) as e:
                self.notify(f"Error saving file: {e}", severity="error")

    def watch_text(self, old_text: str, new_text: str) -> None:
        if old_text != new_text:
            if not self._is_undoing:
                current_cursor = self.cursor_location
                self._undo_stack.append(old_text)
                self._redo_stack.clear()
            
            self._modified = True
            self.post_message(self.FileModified(True))
            
            # Update current tab content
            if self.tabs and self.active_tab_index >= 0:
                self.tabs[self.active_tab_index].content = new_text
                self.tabs[self.active_tab_index].modified = True
        
            if self._syntax:
                self.update_syntax_highlighting() 
            self._update_status_info()

    def action_enter_normal_mode(self) -> None:
        self.mode = "normal"
        self.status_bar.update_mode("NORMAL")
        self.cursor_blink = False

    def action_enter_insert_mode(self) -> None:
        self.mode = "insert"
        self.status_bar.update_mode("INSERT")
        self.cursor_blink = True
        self.cursor_style = "underline" 

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
            lines = self.text.split("\n")
            cur_row, cur_col = self.cursor_location
            line = lines[cur_row] if cur_row < len(lines) else ""
            while cur_col < len(line) and line[cur_col].isspace():
                cur_col += 1
            while cur_col < len(line) and not line[cur_col].isspace():
                cur_col += 1
            self.move_cursor((cur_row, cur_col))

    def action_move_word_backward(self) -> None:
        if self.mode == "normal":
            lines = self.text.split("\n")
            cur_row, cur_col = self.cursor_location
            line = lines[cur_row] if cur_row < len(lines) else ""
            while cur_col > 0 and line[cur_col-1].isspace():
                cur_col -= 1
            while cur_col > 0 and not line[cur_col-1].isspace():
                cur_col -= 1
            self.move_cursor((cur_row, cur_col))

    def action_move_line_start(self) -> None:
        if self.mode == "normal":
            self.move_cursor((self.cursor_location[0], 0))

    def action_undo(self) -> None:
        if self.mode == "normal" and self._undo_stack:
            self._is_undoing = True
            current_cursor = self.cursor_location
            self._redo_stack.append(self.text)
            self.text = self._undo_stack.pop()
            self._is_undoing = False
            max_row = len(self.text.split('\n')) - 1
            row = min(current_cursor[0], max_row)
            line = self.text.split('\n')[row]
            col = min(current_cursor[1], len(line))
            self.move_cursor((row, col))

    def action_redo(self) -> None:
        if self.mode == "normal" and self._redo_stack:
            self._is_undoing = True
            current_cursor = self.cursor_location
            self._undo_stack.append(self.text)
            self.text = self._redo_stack.pop()
            self._is_undoing = False
            max_row = len(self.text.split('\n')) - 1
            row = min(current_cursor[0], max_row)
            line = self.text.split('\n')[row]
            col = min(current_cursor[1], len(line))
            self.move_cursor((row, col))

    def action_delete_char(self) -> None:
        if self.mode == "normal":
            self._save_undo_state()
            cur_row, cur_col = self.cursor_location
            lines = self.text.split("\n")
            if cur_row < len(lines):
                if cur_col < len(lines[cur_row]):
                    lines[cur_row] = lines[cur_row][:cur_col] + lines[cur_row][cur_col + 1:]
                else:
                    lines[cur_row] = lines[cur_row][:cur_col]
                self.text = "\n".join(lines)
                if cur_col < len(lines[cur_row]):
                    self.move_cursor((cur_row, cur_col))
                else:
                    self.move_cursor((cur_row, max(cur_col - 1, 0)))

    def action_delete_line(self) -> None:
        if self.mode == "normal":
            self._save_undo_state()
            cur_row, _ = self.cursor_location
            lines = self.text.split("\n")
            if cur_row < len(lines):
                lines.pop(cur_row)
                self.text = "\n".join(lines)
                self.move_cursor((cur_row, 0))

    def action_delete_to_end(self) -> None:
        if self.mode == "normal":
            self._save_undo_state()
            cur_row, cur_col = self.cursor_location
            lines = self.text.split("\n")
            if cur_row < len(lines):
                line = lines[cur_row]
                start_col = cur_col
                while cur_col < len(line) and not line[cur_col].isspace():
                    cur_col += 1
                lines[cur_row] = line[:start_col] + line[cur_col:]
                self.text = "\n".join(lines)
                self.move_cursor((cur_row, start_col))

    def action_move_line_end(self) -> None:
        if self.mode == "normal":
            lines = self.text.split("\n")
            cur_row = self.cursor_location[0]
            if cur_row < len(lines):
                line_length = len(lines[cur_row])
                self.move_cursor((cur_row, line_length))

    def _save_undo_state(self) -> None:
        if not self._is_undoing:
            self._undo_stack.append(self.text)
            self._redo_stack.clear()

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
            # Check if file is already open in a tab
            for i, tab in enumerate(self.tabs):
                if tab.path == filepath:
                    self.active_tab_index = i
                    self.load_text(tab.content)
                    self.current_file = tab.path
                    self.set_language_from_file(filepath)
                    self._update_status_info()
                    return

            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                new_tab = EditorTab(filepath, content)
                self.tabs.append(new_tab)
                self.active_tab_index = len(self.tabs) - 1
                
                self.load_text(content)
                self.current_file = filepath
                self.set_language_from_file(filepath)
                self._modified = False
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
    ]

    def __init__(self) -> None:
        super().__init__()
        self.show_hidden = False
        self.show_sidebar = True
        self.editor = None

    async def action_new_file(self) -> None:
        editor = self.query_one(CodeEditor)
        await editor.action_new_file()

    def on_file_created(self, event: FileCreated) -> None:
        self.notify(f"Created file: {os.path.basename(event.path)}")
        tree = self.query_one(FilterableDirectoryTree)
        tree.refresh_tree()

    def compose(self) -> ComposeResult:
        yield Container(
            Horizontal(
                Container(
                    Horizontal(
                        Static("Explorer", classes="nav-title"),
                        Button("-", id="toggle_hidden", classes="toggle-hidden-btn"),
                        Button("New", id="new_file", classes="new-file-btn"),
                        classes="nav-header"
                    ),
                    FilterableDirectoryTree(
                        os.path.expanduser("~"),
                        show_hidden=self.show_hidden
                    ),
                    classes="file-nav"
                ),
                Container(
                    CustomCodeEditor(),
                    classes="editor-container"
                ),
                classes="main-container"
            ),
            id="nest-view"
        )

    def on_mount(self) -> None:
        self.editor = self.query_one(CodeEditor)
        tree = self.query_one(FilterableDirectoryTree)
        tree.focus()

        self.editor.can_focus_tab = True
        self.editor.key_handlers = {
            "ctrl+left": lambda: self.action_focus_tree(),
            "ctrl+n": self.action_new_file
        }
        
        tree.key_handlers = {
            "ctrl+n": self.action_new_file
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
            # If the directory tree was focused, focus the code editor
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "toggle_hidden":
            self.action_toggle_hidden()
            event.stop()
        elif event.button.id == "new_file":
            self.run_worker(self.editor.action_new_file())
            event.stop()
        elif event.button.id == "refresh_tree": 
            self.action_refresh_tree()
            event.stop()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        try:
            with open(event.path, 'rb') as file:
                is_binary = False
                chunk = file.read(1024)
                if b'\x00' in chunk or len([b for b in chunk if b > 127]) > chunk.count(b'\n') * 0.3:
                    is_binary = True

            if is_binary:
                self.notify("Cannot open binary file", severity="warning")
                event.stop()
                return

            editor = self.query_one(CodeEditor)
            editor.open_file(event.path)
            editor.focus()
            event.stop()

        except UnicodeDecodeError:
            self.notify("Cannot open file: Not a valid UTF-8 text file", severity="warning")
            event.stop()
        except (IOError, OSError) as e:
            self.notify(f"Error opening file: {str(e)}", severity="error")
            event.stop()

    def get_initial_focus(self) -> Optional[Widget]:
        return self.query_one(FilterableDirectoryTree)

class CustomCodeEditor(CodeEditor):
    BINDINGS = [
        *CodeEditor.BINDINGS,
        Binding("shift+left", "focus_tree", "Focus Tree", show=True)
    ]

    def action_focus_tree(self) -> None:
        self.app.query_one("NestView").action_focus_tree()