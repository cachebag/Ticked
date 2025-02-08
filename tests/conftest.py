import pytest
import tempfile
import os
from ticked.core.database.ticked_db import CalendarDB


@pytest.fixture
def temp_db():
    # Create a temporary file
    fd, path = tempfile.mkstemp()
    os.close(fd)

    # Create database instance with temporary path
    db = CalendarDB(path)

    yield db

    # Cleanup after tests
    try:
        os.unlink(path)
    except:
        pass
