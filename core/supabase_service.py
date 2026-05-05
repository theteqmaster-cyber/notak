import os
import json
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Security: Load credentials from environment
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SESSION_PATH = os.path.expanduser("~/.notak/session.json")

class SupabaseService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseService, cls).__new__(cls)
            cls._instance.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            cls._instance.load_session()
        return cls._instance

    def load_session(self):
        if os.path.exists(SESSION_PATH):
            try:
                with open(SESSION_PATH, 'r') as f:
                    session_data = json.load(f)
                    self.client.auth.set_session(session_data['access_token'], session_data['refresh_token'])
            except:
                pass

    def save_session(self, session):
        os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
        with open(SESSION_PATH, 'w') as f:
            json.dump({
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "user_id": session.user.id
            }, f)

    def sign_in(self, email, password):
        try:
            response = self.client.auth.sign_in_with_password({"email": email, "password": password})
            if response.session:
                self.save_session(response.session)
                return True, "Success"
            return False, "Login failed"
        except Exception as e:
            return False, str(e)

    def sign_out(self):
        try:
            self.client.auth.sign_out()
            if os.path.exists(SESSION_PATH):
                os.remove(SESSION_PATH)
            return True
        except:
            return False

    def is_authenticated(self):
        try:
            return self.client.auth.get_user() is not None
        except:
            return False

    def get_courses(self):
        try:
            response = self.client.table("courses").select("*").order("name").execute()
            return response.data
        except Exception as e:
            print(f"Error fetching courses: {e}")
            return []

    def get_notes_for_course(self, course_id):
        try:
            response = self.client.table("notes").select("*").eq("course_id", course_id).order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching notes for course {course_id}: {e}")
            return []

    def get_all_notes(self):
        try:
            response = self.client.table("notes").select("*").order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching all notes: {e}")
            return []

    def create_note(self, title, course_id, note_type):
        """Initialize a new note in the cloud."""
        try:
            user = self.client.auth.get_user()
            if not user: return None
            
            data = {
                "title": title,
                "course_id": course_id,
                "type": note_type,
                "content": "",
                "user_id": user.user.id
            }
            response = self.client.table("notes").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating note: {e}")
            return None

    def update_note(self, note_id, title, content):
        """Update existing note content in the cloud."""
        try:
            data = {"content": content, "title": title}
            response = self.client.table("notes").update(data).eq("id", note_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error updating note: {e}")
            return None

    def get_timetable(self):
        """Fetch today's classes from the timetable_entries table."""
        try:
            # Python weekday is 0=Mon, 6=Sun. Table day_of_week is likely 1=Mon, 7=Sun.
            day_of_week = datetime.datetime.now().weekday() + 1
            response = self.client.table("timetable_entries").select("*").eq("day_of_week", day_of_week).order("start_time").execute()
            return response.data
        except Exception as e:
            print(f"Error fetching timetable: {e}")
            return []

    def get_calendar_events(self):
        """Fetch today's calendar events from Supabase."""
        try:
            today_start = datetime.datetime.now().strftime("%Y-%m-%dT00:00:00")
            today_end = datetime.datetime.now().strftime("%Y-%m-%dT23:59:59")
            # Using the cloud calendar_events table with start_time range filter
            response = self.client.table("calendar_events").select("*").gte("start_time", today_start).lte("start_time", today_end).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching calendar events: {e}")
            return []
