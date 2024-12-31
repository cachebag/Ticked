from textual.app import ComposeResult
from textual.containers import Horizontal, Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import DirectoryTree, Static, Button, TextArea, Input, Label
from textual.binding import Binding
from textual.message import Message
from rich.syntax import Syntax
from rich.text import Text
import os

class FilterableDirectoryTree(DirectoryTree):
    def __init__(self, path: str, show_hidden: bool = False) -> None:
        super().__init__(path)
        self.show_hidden = show_hidden

    def filter_paths(self, paths: list[str]) -> list[str]:
        if self.show_hidden:
            return paths
        return [path for path in paths if not os.path.basename(path).startswith('.')]

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
        except Exception as e:
            self.notify(f"Error creating file: {str(e)}", severity="error")

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

class CodeEditor(TextArea):
    BINDINGS = [
        Binding("ctrl+n", "new_file", "New File", show=True),
        Binding("tab", "indent", "Indent", show=False),
        Binding("shift+tab", "unindent", "Unindent", show=False),
        Binding("ctrl+]", "indent", "Indent", show=False),
        Binding("ctrl+[", "unindent", "Unindent", show=False),
        Binding("ctrl+/", "toggle_comment", "Toggle Comment", show=True),
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
        super().__init__(language="python", theme="monokai", show_line_numbers=True)  # Remove all parameters from super().__init__()
        self.current_file = None
        self._modified = False
        self.tab_size = 4
        self._syntax = None
        self.language = None
        self.highlight_text = None
        self.mode = "insert"  # Start in insert mode instead of normal

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.mode = "normal"
            event.prevent_default()
            event.stop()
            return

        if self.mode == "normal":
            if event.character == "i":
                self.mode = "insert"
                event.prevent_default()
                event.stop()
            elif event.character in ["h", "j", "k", "l", "w", "b", "0", "$"]:
                action_map = {
                    "h": self.action_move_left,
                    "j": self.action_move_down,
                    "k": self.action_move_up,
                    "l": self.action_move_right,
                    "w": self.action_move_word_forward,
                    "b": self.action_move_word_backward,
                    "0": self.action_move_line_start,
                    "$": self.action_move_line_end
                }
                if event.character in action_map:
                    action_map[event.character]()
                    event.prevent_default()
                    event.stop()
            else:
                if event.is_printable:
                    event.prevent_default()
                    event.stop()

    def execute_command(self) -> None:
        command = self.command[1:].strip()  
        if command == "w":
            self.action_write()
        elif command == "wq":
            self.action_write_quit()
        elif command == "q":
            self.action_quit()
        elif command == "q!":
            self.action_force_quit()
        else:
            self.notify(f"Unknown command: {command}", severity="warning")

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
                    theme="dracula",  # Changed to dracula theme
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
        self.current_file = None
        self._modified = False
        self.notify("File closed. You are now editing a blank file.", severity="info")
        self.refresh()


    def action_write(self) -> None:
        if not self.current_file:
            self.notify("No file to save", severity="warning")
            return
        
        self.action_save_file()

    def action_write_quit(self) -> None:
        if not self.current_file:
            self.notify("No file to save", severity="warning")
            self.clear_editor()
            return
        
        self.action_save_file()
        self.clear_editor()

    def action_quit(self) -> None:
        if self._modified:
            self.notify("You have unsaved changes. Use ':q!' to override.", severity="warning")
        else:
            self.clear_editor()

    def action_force_quit(self) -> None:
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
                self.notify("File saved successfully")
            except (IOError, OSError) as e:
                self.notify(f"Error saving file: {e}", severity="error")

    def watch_text(self, old_text: str, new_text: str) -> None:
        if old_text != new_text:
            if not self._is_undoing:
                self._undo_stack.append(old_text)
                self._redo_stack.clear()
            
            if not self._modified:
                self._modified = True
                self.post_message(self.FileModified(True))
        
            if self._syntax:
                self.update_syntax_highlighting() 

    def action_enter_normal_mode(self) -> None:
        self.mode = "normal"

    def action_enter_insert_mode(self) -> None:
        self.mode = "insert"

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
        if self.mode == "normal":
            self.undo()

    def action_redo(self) -> None:
        if self.mode == "normal":
            self.redo() 

    def action_delete_char(self) -> None:
        if self.mode == "normal":
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
            cur_row, _ = self.cursor_location
            lines = self.text.split("\n")
            if cur_row < len(lines):
                lines.pop(cur_row)
                self.text = "\n".join(lines)
                self.move_cursor((cur_row, 0))

    def action_delete_to_end(self) -> None:
        if self.mode == "normal":
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

    async def action_new_file(self) -> None:
        try:
            tree = self.app.screen.query_one(FilterableDirectoryTree)
            current_path = tree.path if tree.path else os.path.expanduser("~")
        except Exception:
            current_path = os.path.expanduser("~")
            
        dialog = NewFileDialog(current_path)
        result = await self.app.push_screen(dialog)
        
        if result:
            try:
                with open(result, 'r', encoding='utf-8') as file:
                    self.load_text("")
                    self._undo_stack = []
                    self._redo_stack = []
                    self._last_text = ""
                    self.current_file = result
                    self.set_language_from_file(result)
                    self.mode = "normal"
                    self.focus()
                    self.notify(f"Created new file: {os.path.basename(result)}")
            except Exception as e:
                self.notify(f"Error loading new file: {str(e)}", severity="error")

class NestView(Container):
    BINDINGS = [
        Binding("ctrl+h", "toggle_hidden", "Toggle Hidden Files", show=True),
        Binding("ctrl+b", "toggle_sidebar", "Toggle Sidebar", show=True),
        Binding("ctrl+f", "find", "Find", show=True),
        Binding("ctrl+right", "focus_editor", "Focus Editor", show=True),
        Binding("ctrl+left", "focus_tree", "Focus Tree", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.show_hidden = False
        self.show_sidebar = True
        self.editor = None

    async def action_new_file(self) -> None:
        await self.app.action_new_file()

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
        else:
            file_nav.remove_class("hidden")
            
    def action_focus_editor(self) -> None:
        self.query_one(CodeEditor).focus()

    def action_focus_tree(self) -> None:
        self.query_one(FilterableDirectoryTree).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "toggle_hidden":
            self.action_toggle_hidden()
            event.stop()
        elif event.button.id == "new_file":
            self.run_worker(self.action_new_file())
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
                return

            editor = self.query_one(CodeEditor)
            with open(event.path, 'r', encoding='utf-8') as file:
                content = file.read()
                editor.load_text(content)
                editor._undo_stack = []
                editor._redo_stack = []
                editor._last_text = content
                editor.current_file = event.path
                editor.set_language_from_file(event.path)
                editor.mode = "normal"
                editor.focus()

        except UnicodeDecodeError:
            self.notify("Cannot open file: Not a valid UTF-8 text file", severity="warning")
        except (IOError, OSError) as e:
            self.notify(f"Error opening file: {str(e)}", severity="error")

    def on_code_editor_file_modified(self, event: CodeEditor.FileModified) -> None:
        pass

class CustomCodeEditor(CodeEditor):
    BINDINGS = [
        *CodeEditor.BINDINGS,
        Binding("shift+left", "focus_tree", "Focus Tree", show=True)
    ]

    def action_focus_tree(self) -> None:
        self.app.query_one("NestView").action_focus_tree()
