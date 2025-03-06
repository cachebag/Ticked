import os
from datetime import datetime, timedelta

import pytest

from ticked.core.database.ticked_db import CalendarDB


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    import tempfile

    db_fd, db_path = tempfile.mkstemp()
    db = CalendarDB(db_path)
    yield db
    os.close(db_fd)
    os.unlink(db_path)


def test_add_and_get_task(temp_db):
    task_id = temp_db.add_task(
        title="Test Task",
        description="Test Description",
        due_date="2025-01-01",
        start_time="09:00",
        end_time="10:00",
    )

    assert task_id > 0

    tasks = temp_db.get_tasks_for_date("2025-01-01")
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Test Task"
    assert tasks[0]["description"] == "Test Description"
    assert tasks[0]["start_time"] == "09:00"
    assert tasks[0]["end_time"] == "10:00"
    assert tasks[0]["completed"] == 0
    assert tasks[0]["in_progress"] == 0

    tasks = temp_db.get_tasks_for_date("2025-01-02")
    assert len(tasks) == 0


def test_add_multiple_tasks(temp_db):
    temp_db.add_task(
        title="Task 1", due_date="2025-01-01", start_time="09:00", end_time="10:00"
    )

    temp_db.add_task(
        title="Task 2", due_date="2025-01-01", start_time="14:00", end_time="15:00"
    )

    tasks = temp_db.get_tasks_for_date("2025-01-01")
    assert len(tasks) == 2
    assert tasks[0]["title"] == "Task 1"
    assert tasks[0]["start_time"] == "09:00"
    assert tasks[1]["title"] == "Task 2"
    assert tasks[1]["start_time"] == "14:00"


def test_update_task(temp_db):
    task_id = temp_db.add_task(
        title="Original Title",
        due_date="2025-01-01",
        start_time="09:00",
        end_time="10:00",
    )

    success = temp_db.update_task(
        task_id, title="Updated Title", description="Added Description"
    )
    assert success

    success = temp_db.update_task(task_id, completed=True)
    assert success

    tasks = temp_db.get_tasks_for_date("2025-01-01")
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Updated Title"
    assert tasks[0]["description"] == "Added Description"
    assert tasks[0]["completed"] == 1

    success = temp_db.update_task(task_id, completed=False, in_progress=True)
    assert success

    tasks = temp_db.get_tasks_for_date("2025-01-01")
    assert tasks[0]["completed"] == 0
    assert tasks[0]["in_progress"] == 1

    success = temp_db.update_task(
        task_id, due_date="2025-01-02", start_time="13:00", end_time="14:00"
    )
    assert success

    tasks = temp_db.get_tasks_for_date("2025-01-01")
    assert len(tasks) == 0

    tasks = temp_db.get_tasks_for_date("2025-01-02")
    assert len(tasks) == 1
    assert tasks[0]["start_time"] == "13:00"
    assert tasks[0]["end_time"] == "14:00"


def test_update_nonexistent_task(temp_db):
    success = temp_db.update_task(999, title="This task doesn't exist")
    assert not success


def test_delete_task(temp_db):
    task_id = temp_db.add_task(
        title="To Be Deleted",
        due_date="2025-01-01",
        start_time="09:00",
        end_time="10:00",
    )

    other_task_id = temp_db.add_task(
        title="Should Remain",
        due_date="2025-01-01",
        start_time="11:00",
        end_time="12:00",
    )

    tasks = temp_db.get_tasks_for_date("2025-01-01")
    assert len(tasks) == 2

    success = temp_db.delete_task(task_id)
    assert success

    tasks = temp_db.get_tasks_for_date("2025-01-01")
    assert len(tasks) == 1
    assert tasks[0]["id"] == other_task_id

    success = temp_db.delete_task(999)
    assert not success


def test_get_month_stats(temp_db):
    temp_db.add_task(
        title="Task 1",
        due_date="2025-01-01",
        start_time="09:00",
        end_time="10:00",
        description="Test",
    )

    task_id2 = temp_db.add_task(
        title="Task 2",
        due_date="2025-01-05",
        start_time="09:00",
        end_time="10:00",
        description="Test",
    )

    task_id3 = temp_db.add_task(
        title="Task 3",
        due_date="2025-01-10",
        start_time="09:00",
        end_time="10:00",
        description="Test",
    )

    task_id4 = temp_db.add_task(
        title="Task 4",
        due_date="2025-01-15",
        start_time="09:00",
        end_time="10:00",
        description="Test",
    )

    temp_db.add_task(
        title="February Task",
        due_date="2025-02-01",
        start_time="09:00",
        end_time="10:00",
        description="Test",
    )

    temp_db.update_task(task_id2, completed=True)
    temp_db.update_task(task_id3, in_progress=True)

    stats = temp_db.get_month_stats(2025, 1)

    assert stats["total"] == 4
    assert stats["completed"] == 1
    assert stats["in_progress"] == 1
    assert stats["completion_pct"] == 25.0
    assert stats["grade"] == "F"

    temp_db.update_task(task_id3, in_progress=False, completed=True)
    temp_db.update_task(task_id4, completed=True)

    stats = temp_db.get_month_stats(2025, 1)
    assert stats["completed"] == 3
    assert stats["completion_pct"] == 75.0
    assert stats["grade"] == "C"

    stats = temp_db.get_month_stats(2025, 2)
    assert stats["total"] == 1
    assert stats["completed"] == 0
    assert stats["completion_pct"] == 0.0
    assert stats["grade"] == "F"


def test_save_and_get_notes(temp_db):
    date = "2025-01-01"
    content = "Test note content"

    success = temp_db.save_notes(date, content)
    assert success

    retrieved_content = temp_db.get_notes(date)
    assert retrieved_content == content

    new_content = "Updated content"
    success = temp_db.save_notes(date, new_content)
    assert success

    retrieved_content = temp_db.get_notes(date)
    assert retrieved_content == new_content

    nonexistent = temp_db.get_notes("2025-01-02")
    assert nonexistent is None


def test_get_tasks_between_dates(temp_db):
    temp_db.add_task(
        title="Task Day 1",
        due_date="2025-01-01",
        start_time="09:00",
        end_time="10:00",
    )

    temp_db.add_task(
        title="Task Day 3",
        due_date="2025-01-03",
        start_time="09:00",
        end_time="10:00",
    )

    temp_db.add_task(
        title="Task Day 5",
        due_date="2025-01-05",
        start_time="09:00",
        end_time="10:00",
    )

    tasks = temp_db.get_tasks_between_dates("2025-01-02", "2025-01-04")
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Task Day 3"

    tasks = temp_db.get_tasks_between_dates("2025-01-01", "2025-01-05")
    assert len(tasks) == 3

    assert tasks[0]["title"] == "Task Day 1"
    assert tasks[1]["title"] == "Task Day 3"
    assert tasks[2]["title"] == "Task Day 5"


def test_get_upcoming_tasks(temp_db):
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    two_weeks = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

    temp_db.add_task(
        title="Today's Task", due_date=today, start_time="09:00", end_time="10:00"
    )

    temp_db.add_task(
        title="Tomorrow's Task", due_date=tomorrow, start_time="09:00", end_time="10:00"
    )

    temp_db.add_task(
        title="Next Week's Task",
        due_date=next_week,
        start_time="09:00",
        end_time="10:00",
    )

    temp_db.add_task(
        title="Two Weeks Task",
        due_date=two_weeks,
        start_time="09:00",
        end_time="10:00",
    )

    upcoming = temp_db.get_upcoming_tasks(today, days=7)
    assert len(upcoming) == 2
    task_titles = [task["title"] for task in upcoming]
    assert "Tomorrow's Task" in task_titles
    assert "Next Week's Task" in task_titles

    upcoming = temp_db.get_upcoming_tasks(today, days=15)
    assert len(upcoming) == 3

    past_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    upcoming = temp_db.get_upcoming_tasks(past_date, days=7)
    assert len(upcoming) >= 1

    upcoming = temp_db.get_upcoming_tasks(today, days=30)
    assert upcoming[0]["due_date"] == tomorrow
    assert upcoming[-1]["due_date"] == two_weeks


def test_calendar_view_preference(temp_db):
    assert temp_db.get_calendar_view_preference() is False

    temp_db.save_calendar_view_preference(True)
    assert temp_db.get_calendar_view_preference() is True

    temp_db.save_calendar_view_preference(False)
    assert temp_db.get_calendar_view_preference() is False


def test_theme_preference(temp_db):
    assert temp_db.get_theme_preference() is None

    temp_db.save_theme_preference("dark")
    assert temp_db.get_theme_preference() == "dark"

    temp_db.save_theme_preference("light")
    assert temp_db.get_theme_preference() == "light"


def test_notes_view_mode(temp_db):
    date = "2025-01-01"

    assert temp_db.get_notes_view_mode(date) is None

    temp_db.save_notes_view_mode(date, "edit")
    assert temp_db.get_notes_view_mode(date) == "edit"

    temp_db.save_notes_view_mode(date, "view")
    assert temp_db.get_notes_view_mode(date) == "view"

    other_date = "2025-01-02"
    assert temp_db.get_notes_view_mode(other_date) is None

    temp_db.save_notes_view_mode(other_date, "edit")
    assert temp_db.get_notes_view_mode(other_date) == "edit"
    assert temp_db.get_notes_view_mode(date) == "view"


def test_caldav_config(temp_db):
    assert temp_db.get_caldav_config() is None

    temp_db.save_caldav_config(
        url="https://example.com/caldav",
        username="testuser",
        password="testpass",
        calendar="Test Calendar",
    )

    config = temp_db.get_caldav_config()
    assert config is not None
    assert config["url"] == "https://example.com/caldav"
    assert config["username"] == "testuser"
    assert config["password"] == "testpass"
    assert config["selected_calendar"] == "Test Calendar"
    assert "last_sync" in config

    temp_db.save_caldav_config(
        url="https://updated.com/caldav",
        username="newuser",
        password="newpass",
        calendar="Updated Calendar",
    )

    config = temp_db.get_caldav_config()
    assert config["url"] == "https://updated.com/caldav"
    assert config["selected_calendar"] == "Updated Calendar"


def test_task_with_caldav_uid(temp_db):
    task_id = temp_db.add_task(
        title="CalDAV Task",
        due_date="2025-01-01",
        start_time="09:00",
        end_time="10:00",
        caldav_uid="test-uid-123",
    )

    task = temp_db.get_task_by_uid("test-uid-123")
    assert task is not None
    assert task["title"] == "CalDAV Task"

    temp_db.update_task(task_id, title="Updated CalDAV Task")

    task = temp_db.get_task_by_uid("test-uid-123")
    assert task["title"] == "Updated CalDAV Task"

    assert temp_db.get_task_by_uid("nonexistent-uid") is None


def test_delete_tasks_not_in_uids(temp_db):
    temp_db.add_task(
        title="Keep Task 1",
        due_date="2025-01-01",
        start_time="09:00",
        end_time="10:00",
        caldav_uid="keep-uid-1",
    )

    temp_db.add_task(
        title="Keep Task 2",
        due_date="2025-01-02",
        start_time="09:00",
        end_time="10:00",
        caldav_uid="keep-uid-2",
    )

    temp_db.add_task(
        title="Delete Task",
        due_date="2025-01-03",
        start_time="09:00",
        end_time="10:00",
        caldav_uid="delete-uid",
    )

    temp_db.add_task(
        title="No UID Task", due_date="2025-01-04", start_time="09:00", end_time="10:00"
    )

    keep_uids = {"keep-uid-1", "keep-uid-2"}
    temp_db.delete_tasks_not_in_uids(keep_uids)

    assert temp_db.get_task_by_uid("keep-uid-1") is not None
    assert temp_db.get_task_by_uid("keep-uid-2") is not None
    assert temp_db.get_task_by_uid("delete-uid") is None

    tasks = temp_db.get_tasks_for_date("2025-01-04")
    assert len(tasks) == 1
    assert tasks[0]["title"] == "No UID Task"


def test_first_launch(temp_db):
    assert temp_db.is_first_launch() is True

    temp_db.mark_first_launch_complete()
    assert temp_db.is_first_launch() is False
