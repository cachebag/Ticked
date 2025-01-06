from datetime import datetime, timedelta
import caldav
from typing import List, Dict, Any, Optional

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

    def sync_calendar(self, calendar_name: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now() + timedelta(days=365)

        calendar = next((cal for cal in self.principal.calendars() if cal.name == calendar_name), None)
        if not calendar:
            return []

        events = calendar.date_search(start=start_date, end=end_date)
        
        imported_tasks = []
        for event in events:
            vevent = event.vobject_instance.vevent
            
            title = str(getattr(vevent, 'summary', 'No Title')).replace('<SUMMARY>', '').replace('</SUMMARY>', '')
            description = str(getattr(vevent, 'description', '')).replace('<DESCRIPTION>', '').replace('</DESCRIPTION>', '')
            
            start_time = vevent.dtstart.value
            
            if isinstance(start_time, datetime):
                due_date = start_time.strftime('%Y-%m-%d')
                due_time = start_time.strftime('%H:%M')
            else:
                due_date = start_time.strftime('%Y-%m-%d')
                due_time = '00:00'
                
            task_id = self.db.add_task(
                title=title,
                description=description,
                due_date=due_date,
                due_time=due_time
            )
            
            if task_id:
                imported_tasks.append({
                    'id': task_id,
                    'title': title,
                    'description': description,
                    'due_date': due_date,
                    'due_time': due_time
                })
        
        return imported_tasks