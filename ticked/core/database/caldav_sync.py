# caldav_sync.py
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
            print(f"Connection error: {e}")
            return False
            
    def get_calendars(self) -> List[str]:
        try:
            calendars = self.principal.calendars()
            calendar_names = []
            for cal in calendars:
                if cal.name:
                    raw_name = cal.name.replace("⚠️", "").strip()
                    # Remove both single and double quotes around the edges
                    raw_name = raw_name.strip("'\"")

                    if raw_name:
                        calendar_names.append(raw_name)
            return calendar_names
        except Exception as e:
            print(f"Error getting calendars: {e}")
            return []


    def sync_calendar(self, calendar_name: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now() + timedelta(days=365)
        
        try:
            calendar = next((cal for cal in self.principal.calendars() 
                            if cal.name.replace('⚠️', '').strip() == calendar_name), None)
            if not calendar:
                print(f"Calendar not found: {calendar_name}")
                return []

            events = calendar.date_search(start=start_date, end=end_date)
            imported_tasks = []
            event_uids = set()

            for event in events:
                vevent = event.vobject_instance.vevent
                
                title = str(getattr(vevent, 'summary', 'No Title')).replace('<SUMMARY>', '').replace('</SUMMARY>', '')
                description = str(getattr(vevent, 'description', '')).replace('<DESCRIPTION>', '').replace('</DESCRIPTION>', '')
                
                start_time = vevent.dtstart.value
                end_time = getattr(vevent, 'dtend', None)
                if end_time:
                    end_time = end_time.value
                else:
                    end_time = start_time + timedelta(hours=1) if isinstance(start_time, datetime) else start_time

                if isinstance(start_time, datetime):
                    due_date = start_time.strftime('%Y-%m-%d')
                    start_time_str = start_time.strftime('%H:%M')
                    end_time_str = end_time.strftime('%H:%M')
                else:
                    due_date = start_time.strftime('%Y-%m-%d')
                    start_time_str = '00:00'
                    end_time_str = '23:59'

                caldav_uid = str(getattr(vevent, 'uid', ''))
                event_uids.add(caldav_uid)

                existing_task = self.db.get_task_by_uid(caldav_uid)
                if existing_task:
                    self.db.update_task(
                        existing_task['id'],
                        title=title,
                        description=description,
                        due_date=due_date,
                        start_time=start_time_str,
                        end_time=end_time_str
                    )
                    task_id = existing_task['id']
                else:
                    task_id = self.db.add_task(
                        title=title,
                        description=description,
                        due_date=due_date,
                        start_time=start_time_str,
                        end_time=end_time_str,
                        caldav_uid=caldav_uid
                    )

                if task_id:
                    imported_tasks.append({
                        'id': task_id,
                        'title': title,
                        'description': description,
                        'due_date': due_date,
                        'start_time': start_time_str,
                        'end_time': end_time_str,
                        'caldav_uid': caldav_uid
                    })

            self.db.delete_tasks_not_in_uids(event_uids)
            return imported_tasks

        except Exception as e:
            print(f"Error syncing calendar: {e}")
            return []