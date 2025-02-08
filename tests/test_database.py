import pytest
from datetime import datetime, timedelta


def test_add_and_get_task(temp_db):
    # Test adding a task
    task_id = temp_db.add_task(
        title="Test Task",
        description="Test Description",
        due_date="2025-01-01",
        start_time="09:00",
        end_time="10:00",
    )

    assert task_id > 0

    # Test getting tasks for the date
    tasks = temp_db.get_tasks_for_date("2025-01-01")
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Test Task"
    assert tasks[0]["description"] == "Test Description"
    assert tasks[0]["start_time"] == "09:00"
    assert tasks[0]["end_time"] == "10:00"


def test_update_task(temp_db):
    # Add a task first
    task_id = temp_db.add_task(
        title="Original Title",
        due_date="2025-01-01",
        start_time="09:00",
        end_time="10:00",
    )

    # Update the task
    success = temp_db.update_task(
        task_id, title="Updated Title", description="Added Description"
    )
    assert success

    # Verify the update
    tasks = temp_db.get_tasks_for_date("2025-01-01")
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Updated Title"
    assert tasks[0]["description"] == "Added Description"


def test_delete_task(temp_db):
    # Add a task
    task_id = temp_db.add_task(
        title="To Be Deleted",
        due_date="2025-01-01",
        start_time="09:00",
        end_time="10:00",
    )

    # Verify it exists
    tasks = temp_db.get_tasks_for_date("2025-01-01")
    assert len(tasks) == 1

    # Delete it
    success = temp_db.delete_task(task_id)
    assert success

    # Verify it's gone
    tasks = temp_db.get_tasks_for_date("2025-01-01")
    assert len(tasks) == 0


def test_get_month_stats(temp_db):
    # Add some tasks
    temp_db.add_task(
        title="Task 1",
        due_date="2025-01-01",
        start_time="09:00",
        end_time="10:00",
        description="Test",
    )

    task_id = temp_db.add_task(
        title="Task 2",
        due_date="2025-01-02",
        start_time="09:00",
        end_time="10:00",
        description="Test",
    )

    # Mark one task as completed
    temp_db.update_task(task_id, completed=True)

    # Get stats for January 2025
    stats = temp_db.get_month_stats(2025, 1)

    assert stats["total"] == 2
    assert stats["completed"] == 1
    assert stats["in_progress"] == 0
    assert stats["completion_pct"] == 50.0


def test_save_and_get_notes(temp_db):
    date = "2025-01-01"
    content = "Test note content"

    # Save notes
    success = temp_db.save_notes(date, content)
    assert success

    # Retrieve notes
    retrieved_content = temp_db.get_notes(date)
    assert retrieved_content == content

    # Test updating existing notes
    new_content = "Updated content"
    success = temp_db.save_notes(date, new_content)
    assert success

    retrieved_content = temp_db.get_notes(date)
    assert retrieved_content == new_content


def test_get_upcoming_tasks(temp_db):
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

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

    # Test 7-day upcoming tasks
    upcoming = temp_db.get_upcoming_tasks(today, days=7)
    assert len(upcoming) == 2  # Should include tomorrow's and next week's tasks

    # Test 30-day upcoming tasks
    upcoming = temp_db.get_upcoming_tasks(today, days=30)
    assert len(upcoming) == 2  # Should include tomorrow's and next week's tasks

    # Verify the specific tasks are the ones we expect
    task_titles = {task["title"] for task in upcoming}
    assert "Tomorrow's Task" in task_titles
    assert "Next Week's Task" in task_titles
    assert "Today's Task" not in task_titles  # Today's task should be excluded
