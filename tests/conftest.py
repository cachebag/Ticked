import pytest
import os
import tempfile
import shutil
from typing import Generator, Dict, Any
from ticked.core.database.ticked_db import CalendarDB


@pytest.fixture
def temp_db():
    db_fd, db_path = tempfile.mkstemp()
    db = CalendarDB(db_path)
    yield db
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def test_env() -> Generator[Dict[str, Any], None, None]:
    old_env = os.environ.copy()
    temp_home = tempfile.mkdtemp()
    os.environ["HOME"] = temp_home
    os.environ["PYTEST_RUNNING"] = "1"

    yield {
        "temp_home": temp_home,
    }

    os.environ.clear()
    os.environ.update(old_env)

    shutil.rmtree(temp_home)


@pytest.fixture
def mock_jedi_completions():
    class MockCompletion:
        def __init__(self, name, type_, desc):
            self.name = name
            self.type = type_
            self.description = desc
            self.score = 0

    return [
        MockCompletion("print", "function", "Print objects to the text stream"),
        MockCompletion("len", "function", "Return the length of an object"),
        MockCompletion("str", "function", "Return a string version of an object"),
        MockCompletion("list", "function", "Create a new list"),
    ]
