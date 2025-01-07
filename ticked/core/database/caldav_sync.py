from datetime import datetime, timedelta
import caldav
from typing import List, Dict, Any, Optional
import re

class CalDAVSync:
    def __init__(self, db):
        self.db = db
        
    def connect(self, url: str, username: str, password: str) -> bool:
        try:
            self.client = caldav.DAVClient(
                url=url,
                username=username,
                password=password
            )
            self.principal = self.client.principal()
            return True
        except Exception as e:
            return False

    def get_calendars(self) -> List[str]:
        try:
            calendars = self.principal.calendars()
            return [cal.name.replace('⚠️', '').strip() for cal in calendars if cal.name]
        except Exception as e:
            print(f"Error getting calendars: {e}")
            return []

    def _clean_text(self, text: str) -> str:
        # Convert to string in case we get a non-string type
        text = str(text)
        
        # Remove only XML/HTML tags while preserving content
        cleaned = re.sub(r'<[^>]+>', '', text)
        
        # Clean up any extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        # Remove specific XML-like tags that might appear in caldav events
        cleaned = cleaned.replace('<SUMMARY>', '').replace('</SUMMARY>', '')
        cleaned = cleaned.replace('<DESCRIPTION>', '').replace('</DESCRIPTION>', '')
        
        return cleaned.strip()

    def _task_exists(self, title: str, due_date: str) -> bool:
        existing_tasks = self.db.get_tasks_for_date(due_date)
        return any(task['title'] == title for task in existing_tasks)

    def sync_calendar(self, calendar_name: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now() + timedelta(days=365)

        calendar = next((cal for cal in self.principal.calendars() if cal.name == calendar_name), None)
        if not calendar:
            return []

        events = calendar.date_search(start=start_date, end=end_date)
        current_event_uids = set()
        imported_tasks = []

        for event in events:
            vevent = event.vobject_instance.vevent
            current_event_uids.add(str(vevent.uid.value))
            
            title = self._clean_text(str(vevent.summary.value)) if hasattr(vevent, 'summary') else 'No Title'
            description = self._clean_text(str(vevent.description.value)) if hasattr(vevent, 'description') else ''
            
            # Handle start and end times
            start_time = vevent.dtstart.value
            end_time = vevent.dtend.value if hasattr(vevent, 'dtend') else start_time
            
            if isinstance(start_time, datetime):
                due_date = start_time.strftime('%Y-%m-%d')
                start_time_str = start_time.strftime('%H:%M')
                end_time_str = end_time.strftime('%H:%M')
            else:
                due_date = start_time.strftime('%Y-%m-%d')
                start_time_str = '00:00'
                end_time_str = '23:59'
                
            existing_task = self.db.get_task_by_uid(str(vevent.uid.value))
            
            if existing_task:
                self.db.update_task(
                    existing_task['id'],
                    title=title,
                    description=description,
                    due_date=due_date,
                    start_time=start_time_str,
                    end_time=end_time_str
                )
            else:
                self.db.add_task(
                    title=title,
                    description=description,
                    due_date=due_date,
                    start_time=start_time_str,
                    end_time=end_time_str,
                    caldav_uid=str(vevent.uid.value)
                )

        self.db.delete_tasks_not_in_uids(current_event_uids)
        return imported_tasks