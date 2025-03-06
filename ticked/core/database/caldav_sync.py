import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import caldav


class CalDAVSync:
    def __init__(self, db):
        self.db = db

    def connect(self, url: str, username: str, password: str) -> bool:
        try:
            self.client = caldav.DAVClient(
                url=url, username=username, password=password
            )
            self.principal = self.client.principal()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def get_calendars(self) -> List[str]:
        try:
            calendars = self.principal.calendars()
            calendar_names = []
            for cal in calendars:
                if cal.name:
                    clean_name = cal.name
                    clean_name = clean_name.replace("⚠️", "").strip()
                    clean_name = re.sub(r'^[\'"]|[\'"]$', "", clean_name)
                    clean_name = clean_name.strip()

                    if clean_name:
                        calendar_names.append(clean_name)

            return sorted(set(calendar_names))
        except Exception as e:
            return []

    def sync_calendar(
        self,
        calendar_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now() + timedelta(days=365)

        try:
            calendar = next(
                (
                    cal
                    for cal in self.principal.calendars()
                    if cal.name.replace("⚠️", "").strip() == calendar_name
                ),
                None,
            )
            if not calendar:
                return []

            events = calendar.date_search(start=start_date, end=end_date)
            imported_tasks = []
            event_uids = set()

            for event in events:
                vevent = event.vobject_instance.vevent

                summary = getattr(vevent, "summary", None)
                if hasattr(summary, "value"):
                    title = str(summary.value)
                elif summary is not None:
                    title = str(summary)
                else:
                    title = "No Title"
                title = re.sub(r"<[^>]+>", "", title).strip() or "No Title"

                desc = getattr(vevent, "description", None)
                if hasattr(desc, "value"):
                    description = str(desc.value)
                elif desc is not None:
                    description = str(desc)
                else:
                    description = ""
                description = re.sub(r"<[^>]+>", "", description).strip()

                start_time = vevent.dtstart.value
                end_time = getattr(vevent, "dtend", None)

                is_all_day = not isinstance(start_time, datetime)

                if is_all_day:
                    start_time_str = "00:00"
                    end_time_str = "23:59"
                    due_date = start_time.strftime("%Y-%m-%d")
                else:
                    due_date = start_time.strftime("%Y-%m-%d")
                    start_time_str = start_time.strftime("%H:%M")
                    if end_time:
                        end_time = end_time.value
                        end_time_str = end_time.strftime("%H:%M")
                    else:
                        end_time_str = (start_time + timedelta(hours=1)).strftime(
                            "%H:%M"
                        )

                caldav_uid = str(getattr(vevent, "uid", ""))
                event_uids.add(caldav_uid)

                existing_task = self.db.get_task_by_uid(caldav_uid)
                if existing_task:
                    self.db.update_task(
                        existing_task["id"],
                        title=title,
                        description=description,
                        due_date=due_date,
                        start_time=start_time_str,
                        end_time=end_time_str,
                    )
                    task_id = existing_task["id"]
                else:
                    task_id = self.db.add_task(
                        title=title,
                        description=description,
                        due_date=due_date,
                        start_time=start_time_str,
                        end_time=end_time_str,
                        caldav_uid=caldav_uid,
                    )

                if task_id:
                    imported_tasks.append(
                        {
                            "id": task_id,
                            "title": title,
                            "description": description,
                            "due_date": due_date,
                            "start_time": start_time_str,
                            "end_time": end_time_str,
                            "caldav_uid": caldav_uid,
                        }
                    )

            self.db.delete_tasks_not_in_uids(event_uids)
            return imported_tasks

        except Exception as e:
            return []
