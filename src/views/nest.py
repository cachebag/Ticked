from textual.app import ComposeResult
from textual.containers import Horizontal, Container
from textual.widgets import DirectoryTree, Static, Button, TextArea
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

class CodeEditor(TextArea):
    BINDINGS = [
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
    ]

    class FileModified(Message):
        def __init__(self, is_modified: bool) -> None:
            super().__init__()
            self.is_modified = is_modified

    def __init__(self) -> None:
        super().__init__()
        self.current_file = None
        self._modified = False
        self.tab_size = 4
        self._syntax = None
        self.language = None
        self.highlight_text = None
        self.mode = "insert"

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.mode = "normal"
            event.prevent_default()
            event.stop()
            return

        if self.mode == "normal":
            # In normal mode, only allow command keys
            if event.character == "i":
                self.mode = "insert"
                event.prevent_default()
                event.stop()
            elif event.character in ["h", "j", "k", "l", "w", "b", "0", "$"]:
                # Map the keys to their corresponding actions
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
                # Prevent any text input in normal mode
                if event.is_printable:
                    event.prevent_default()
                    event.stop()

    def set_language_from_file(self, filepath: str) -> None:
        ext = os.path.splitext(filepath)[1].lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.html': 'html',
            '.css': 'css',
            '.md': 'markdown',
        }
        self.language = language_map.get(ext, None)
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
            except (SyntaxError, ValueError) as e:
                self.notify(f"Syntax highlighting error: {e}", severity="error")

    def update_syntax_highlighting(self) -> None:
        if self.language and self.text and self._syntax:
            try:
                self._syntax.code = self.text
                rich_text = Text.from_ansi(str(self._syntax))
                self.highlight_text = rich_text
            except (SyntaxError, ValueError) as e:
                self.notify(f"Highlighting update error: {e}", severity="error")

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

    def action_move_line_end(self) -> None:
        if self.mode == "normal":
            lines = self.text.split("\n")
            cur_row = self.cursor_location[0]
            line_length = len(lines[cur_row]) if cur_row < len(lines) else 0
            self.move_cursor((cur_row, line_length)) 

class NestView(Container):
    BINDINGS = [
        Binding("ctrl+h", "toggle_hidden", "Toggle Hidden Files", show=True),
        Binding("ctrl+b", "toggle_sidebar", "Toggle Sidebar", show=True),
        Binding("ctrl+f", "find", "Find", show=True),
        Binding("space+e", "toggle_sidebar", "Toggle Sidebar", show=True),
        Binding("ctrl+right", "focus_editor", "Focus Editor", show=True),
        Binding("ctrl+left", "focus_tree", "Focus Tree", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.show_hidden = False
        self.show_sidebar = True
        self.editor = None

    def compose(self) -> ComposeResult:
        yield Container(
            Horizontal(
                Container(
                    Horizontal(
                        Static("Explorer", classes="nav-title"),
                        Button("👁", id="toggle_hidden", classes="toggle-hidden-btn"),
                        classes="nav-header"
                    ),
                    FilterableDirectoryTree(
                        os.path.expanduser("~"),
                        show_hidden=self.show_hidden
                    ),
                    classes="file-nav"
                ),
                Container(
                    CodeEditor(),
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

    def action_toggle_hidden(self) -> None:
        self.show_hidden = not self.show_hidden
        tree = self.query_one(FilterableDirectoryTree)
        tree.show_hidden = self.show_hidden
        tree.reload()
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

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        try:
            editor = self.query_one(CodeEditor)
            with open(event.path, 'r', encoding='utf-8') as file:
                editor.load_text(file.read())
            editor.current_file = event.path
            editor.set_language_from_file(event.path)
            editor.focus()
        except (IOError, OSError) as e:
            self.notify(f"Error: {e}", severity="error")

    def on_code_editor_file_modified(self, event: CodeEditor.FileModified) -> None:
        pass
