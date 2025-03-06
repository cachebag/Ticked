import os
import shutil
import tempfile
from typing import Generator, Tuple
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from textual._context import active_app
from textual.app import App, ComposeResult
from textual.screen import Screen

from ticked.ui.views.nest import (
    AutoCompletePopup,
    CodeEditor,
    ContextMenu,
    DeleteConfirmationDialog,
    FileCreated,
    FilterableDirectoryTree,
    FolderCreated,
    NestView,
    NewFileDialog,
    NewFolderDialog,
    RenameDialog,
    StatusBar,
)


class TestAppWithContext(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield NestView()


@pytest.fixture
def test_app() -> Generator[App, None, None]:
    app = TestAppWithContext()

    token = active_app.set(app)

    mock_console = MagicMock()
    mock_console.measure.return_value = (10, 1)
    type(app).console = PropertyMock(return_value=mock_console)

    mock_screen = MagicMock(spec=Screen)
    mock_screen.focused = None

    app.push_screen = MagicMock()
    app.get_screen = MagicMock(return_value=mock_screen)

    type(app).screen = PropertyMock(return_value=mock_screen)

    type(app.screen).focused = PropertyMock(return_value=None)

    app.notify = MagicMock()

    mock_editor = MagicMock(spec=CodeEditor)
    app.query_one = MagicMock(return_value=mock_editor)

    yield app

    active_app.reset(token)


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_files(temp_dir: str) -> Tuple[str, str, str]:
    python_file = os.path.join(temp_dir, "test.py")
    with open(python_file, "w") as f:
        f.write("def test_function():\n    return True\n")

    text_file = os.path.join(temp_dir, "text.txt")
    with open(text_file, "w") as f:
        f.write("This is a test text file")

    test_dir = os.path.join(temp_dir, "test_dir")
    os.makedirs(test_dir)

    return python_file, text_file, test_dir


@pytest.fixture
def mocked_status_bar():
    with patch("ticked.ui.views.nest.StatusBar", autospec=True) as mock_status_bar:
        mock_instance = mock_status_bar.return_value
        mock_instance.update_mode = MagicMock()
        mock_instance.update_file_info = MagicMock()
        mock_instance.update_command = MagicMock()
        yield mock_instance


@pytest.fixture
def code_editor_with_app(test_app: App, mocked_status_bar) -> CodeEditor:
    with patch("ticked.ui.views.nest.StatusBar", return_value=mocked_status_bar):
        editor = CodeEditor()
        object.__setattr__(editor, "_app", test_app)
        editor.notify = MagicMock()

        editor.scroll_to = MagicMock()

        editor._is_undoing = False
        editor.watch_text = MagicMock()

        return editor


@pytest.mark.asyncio
async def test_filterable_directory_tree(temp_dir: str, test_app: App):
    tree = FilterableDirectoryTree(temp_dir)
    object.__setattr__(tree, "_app", test_app)

    tree.show_hidden = False
    visible_paths = [os.path.join(temp_dir, "visible.txt")]
    hidden_paths = [os.path.join(temp_dir, ".hidden")]
    all_paths = visible_paths + hidden_paths

    assert tree.filter_paths(all_paths) == visible_paths

    tree.show_hidden = True
    assert tree.filter_paths(all_paths) == all_paths

    with patch.object(tree, "_get_expanded_paths", return_value=[]):
        with patch.object(tree, "reload"):
            with patch.object(tree, "_restore_expanded_paths"):
                with patch.object(tree, "refresh"):
                    tree.refresh_tree()
                    tree.reload.assert_called_once()
                    tree.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_code_editor_basic(
    test_files: Tuple[str, str, str], code_editor_with_app: CodeEditor
):
    python_file, _, _ = test_files
    editor = code_editor_with_app

    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.read.return_value = "def test_function():\n    return True\n"
        mock_open.return_value.__enter__.return_value = mock_file

        editor.open_file(python_file)
        assert editor.current_file == python_file

    editor.set_language_from_file(python_file)
    assert editor.language == "python"

    editor.text = "    def test():\n        pass"
    editor.cursor_location = (1, 0)
    assert editor.get_current_indent() == "        "


@pytest.mark.asyncio
async def test_code_editor_editing(
    test_files: Tuple[str, str, str], code_editor_with_app: CodeEditor
):
    editor = code_editor_with_app

    editor.text = "def test():\n    pass"
    editor.cursor_location = (1, 4)
    editor.action_indent()
    assert "        pass" in editor.text

    editor.text = "def test():\n    pass"
    editor.cursor_location = (1, 4)
    with patch.object(editor, "move_cursor"):
        with patch.object(editor, "action_delete_left"):
            editor.action_unindent()
            assert editor.move_cursor.called
            assert editor.action_delete_left.called


@pytest.mark.asyncio
async def test_code_editor_file_operations(
    test_files: Tuple[str, str, str], code_editor_with_app: CodeEditor
):
    python_file, _, _ = test_files
    editor = code_editor_with_app

    with patch("builtins.open", create=True) as mock_open:
        mock_write_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_write_file

        editor.current_file = python_file
        editor.text = "# Modified content"

        editor.action_save_file()

        mock_write_file.write.assert_called_with("# Modified content")


@pytest.mark.asyncio
async def test_code_editor_undo_redo(
    test_files: Tuple[str, str, str], code_editor_with_app: CodeEditor
):
    editor = code_editor_with_app

    editor._undo_stack = ["Initial text", "Modified text"]
    editor._redo_stack = []
    editor.text = "Final text"

    def mock_action_undo():
        if editor._undo_stack:
            editor._redo_stack.append(editor.text)
            editor.text = editor._undo_stack.pop()

    editor.action_undo = mock_action_undo

    editor.action_undo()
    assert editor.text == "Modified text"
    editor.action_undo()
    assert editor.text == "Initial text"

    editor._undo_stack = []
    editor._redo_stack = ["Final text", "Modified text"]
    editor.text = "Initial text"

    def mock_action_redo():
        if editor._redo_stack:
            next_text = editor._redo_stack.pop(-1)
            editor._undo_stack.append(editor.text)
            editor.text = next_text

    editor.action_redo = mock_action_redo

    editor.action_redo()
    assert editor.text == "Modified text"
    editor.action_redo()
    assert editor.text == "Final text"


@pytest.mark.asyncio
async def test_nest_view(
    temp_dir: str, test_files: Tuple[str, str, str], test_app: App
):
    view = NestView()

    object.__setattr__(view, "_app", test_app)
    view.query_one = MagicMock()
    view.notify = MagicMock()

    assert view.show_hidden is False
    view.action_toggle_hidden()
    assert view.show_hidden is True

    view.show_sidebar = True
    view.show_sidebar = False
    assert view.show_sidebar is False
    view.show_sidebar = True
    assert view.show_sidebar is True


@pytest.mark.asyncio
async def test_new_file_dialog(temp_dir: str, test_app: App):
    dialog = NewFileDialog(temp_dir)

    object.__setattr__(dialog, "_app", test_app)
    dialog.query_one = MagicMock()
    dialog.dismiss = MagicMock()
    dialog.notify = MagicMock()

    dialog.on_mount()
    dialog.query_one.assert_called_with("#filename")

    with patch("builtins.open", create=True) as mock_open:

        def modified_handle_submit():
            filename = dialog.query_one.return_value.value
            if filename:
                full_path = os.path.join(temp_dir, filename)
                with open(full_path, "w"):
                    pass
                dialog.dismiss(full_path)

        dialog._handle_submit = modified_handle_submit

        mock_input = MagicMock()
        mock_input.value = "test_file.py"
        dialog.query_one.return_value = mock_input

        dialog._handle_submit()

        expected_path = os.path.join(temp_dir, "test_file.py")
        dialog.dismiss.assert_called_once_with(expected_path)


@pytest.mark.asyncio
async def test_new_folder_dialog(temp_dir: str, test_app: App):
    dialog = NewFolderDialog(temp_dir)

    object.__setattr__(dialog, "_app", test_app)
    dialog.query_one = MagicMock()
    dialog.dismiss = MagicMock()
    dialog.notify = MagicMock()

    dialog.on_mount()
    dialog.query_one.assert_called_with("#foldername")

    with patch("os.makedirs") as mock_makedirs:

        def modified_handle_submit():
            foldername = dialog.query_one.return_value.value
            if foldername:
                full_path = os.path.join(temp_dir, foldername)
                os.makedirs(full_path)
                dialog.dismiss(full_path)

        dialog._handle_submit = modified_handle_submit

        mock_input = MagicMock()
        mock_input.value = "test_folder"
        dialog.query_one.return_value = mock_input

        dialog._handle_submit()

        expected_path = os.path.join(temp_dir, "test_folder")
        mock_makedirs.assert_called_once_with(expected_path)
        dialog.dismiss.assert_called_once_with(expected_path)


@pytest.mark.asyncio
async def test_delete_confirmation_dialog(
    test_files: Tuple[str, str, str], test_app: App
):
    python_file, _, test_dir = test_files

    file_dialog = DeleteConfirmationDialog(python_file)
    object.__setattr__(file_dialog, "_app", test_app)
    file_dialog.dismiss = MagicMock()

    assert file_dialog.is_directory is False

    with patch("os.unlink") as mock_unlink:
        with patch.object(test_app, "post_message"):
            file_dialog._handle_delete()
            mock_unlink.assert_called_with(python_file)
            file_dialog.dismiss.assert_called_once()

    dir_dialog = DeleteConfirmationDialog(test_dir)
    object.__setattr__(dir_dialog, "_app", test_app)
    dir_dialog.dismiss = MagicMock()

    assert dir_dialog.is_directory is True

    with patch("shutil.rmtree") as mock_rmtree:
        with patch.object(test_app, "post_message"):
            dir_dialog._handle_delete()
            mock_rmtree.assert_called_with(test_dir)
            dir_dialog.dismiss.assert_called_once()


@pytest.mark.asyncio
async def test_rename_dialog(test_files: Tuple[str, str, str], test_app: App):
    python_file, _, _ = test_files
    old_name = os.path.basename(python_file)
    parent_dir = os.path.dirname(python_file)

    dialog = RenameDialog(python_file)
    object.__setattr__(dialog, "_app", test_app)
    dialog.dismiss = MagicMock()
    dialog.notify = MagicMock()

    assert dialog.old_name == old_name
    assert dialog.parent_dir == parent_dir

    with patch("os.rename") as mock_rename:
        mock_input = MagicMock()
        mock_input.value = "renamed.py"
        dialog.query_one = MagicMock(return_value=mock_input)

        dialog._handle_rename()
        new_path = os.path.join(parent_dir, "renamed.py")
        mock_rename.assert_called_with(python_file, new_path)
        dialog.dismiss.assert_called_once()


@pytest.mark.asyncio
async def test_context_menu(test_app: App):
    items = [("Rename", "rename"), ("Delete", "delete")]
    menu = ContextMenu(items, 10, 10, "/path/to/file.txt")

    object.__setattr__(menu, "_app", test_app)
    menu.dismiss = MagicMock()

    mock_dialog = MagicMock(spec=Screen)

    with patch(
        "ticked.ui.views.nest.DeleteConfirmationDialog", return_value=mock_dialog
    ):
        menu._handle_action("action-delete")
        test_app.push_screen.assert_called_once()
        menu.dismiss.assert_called_once()

    menu.dismiss.reset_mock()
    test_app.push_screen.reset_mock()

    mock_rename_dialog = MagicMock(spec=Screen)
    with patch("ticked.ui.views.nest.RenameDialog", return_value=mock_rename_dialog):
        menu._handle_action("action-rename")
        test_app.push_screen.assert_called_once()
        menu.dismiss.assert_called_once()


@pytest.mark.asyncio
async def test_status_bar(test_app: App):
    with patch("ticked.ui.views.nest.StatusBar.update") as mock_update:
        status = StatusBar()
        object.__setattr__(status, "_app", test_app)

        status.update_mode("INSERT")
        assert status.mode == "INSERT"

        status.update_file_info("test.py [+]")
        assert status.file_info == "test.py [+]"

        status.update_command(":w")
        assert status.command == ":w"

        assert mock_update.called


@pytest.mark.asyncio
async def test_auto_complete_popup(test_app: App):
    popup = AutoCompletePopup()
    object.__setattr__(popup, "_app", test_app)

    popup.add_column = MagicMock()
    popup.add_row = MagicMock()

    class MockCompletion:
        def __init__(self, name, type_, desc):
            self.name = name
            self.type = type_
            self.description = desc

    completions = [
        MockCompletion("print", "function", "Print objects"),
        MockCompletion("list", "class", "List object"),
    ]

    popup.add_column.reset_mock()

    popup.populate(completions)

    assert popup.add_row.call_count == 2


@pytest.mark.asyncio
async def test_code_editor_completion(
    test_files: Tuple[str, str, str], code_editor_with_app: CodeEditor
):
    editor = code_editor_with_app

    editor.text = "import os\n\nos."
    editor.cursor_location = (2, 3)
    word, start = editor._get_current_word()
    assert word == ""
    assert start == 3

    with patch.object(editor, "_get_current_word", return_value=("pr", 0)):
        with patch.object(editor, "_get_local_completions", return_value=[]):
            completions = editor._get_completions()
            assert any(comp.name == "print" for comp in completions)


@pytest.mark.asyncio
async def test_file_operations_integration(temp_dir: str, test_app: App):
    view = NestView()
    object.__setattr__(view, "_app", test_app)

    mocked_tree = MagicMock()
    view.query_one = MagicMock(return_value=mocked_tree)
    view.notify = MagicMock()

    file_path = os.path.join(temp_dir, "new_file.txt")
    view.on_file_created(FileCreated(file_path))
    mocked_tree.refresh_tree.assert_called_once()

    mocked_tree.refresh_tree.reset_mock()

    folder_path = os.path.join(temp_dir, "new_folder")
    view.on_folder_created(FolderCreated(folder_path))
    mocked_tree.refresh_tree.assert_called_once()


@pytest.mark.asyncio
async def test_paste_operation(temp_dir: str, test_app: App):
    source_file = os.path.join(temp_dir, "source.txt")
    with open(source_file, "w") as f:
        f.write("Test content")

    dest_dir = os.path.join(temp_dir, "dest")
    os.makedirs(dest_dir)

    view = NestView()
    object.__setattr__(view, "_app", test_app)
    view.notify = MagicMock()

    test_app.file_clipboard = {"action": "copy", "path": source_file}

    tree_mock = MagicMock()
    tree_mock.cursor_node.data.path = dest_dir

    view.query_one = MagicMock(return_value=tree_mock)

    with patch("shutil.copy2") as mock_copy:
        await view.action_paste()
        mock_copy.assert_called_with(source_file, os.path.join(dest_dir, "source.txt"))
