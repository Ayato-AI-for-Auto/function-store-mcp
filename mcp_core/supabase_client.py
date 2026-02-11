import os
import json
import logging
from typing import Optional, Dict, Any, List
from supabase import create_client
from mcp_core.config import DATA_DIR

logger = logging.getLogger(__name__)

# Constants for Official Public Function Store (MVP)
# これらのキーは「公開ストア」用なので、バイナリに含めてOK（Anon Key）。
DEFAULT_SUPABASE_URL = "https://luzaaubwzvzuqaflveg.supabase.co"
# Note: Key value from image (truncated in UI). Please ensure the full string is used.
DEFAULT_SUPABASE_KEY = "sb_publishable_Q_VJkOLYPXMLtrhbulS9YQ_62EM659S" # ユーザー提供の画像に基づく暫定値

SUPABASE_URL = os.getenv("SUPABASE_URL", DEFAULT_SUPABASE_URL)
SUPABASE_KEY = os.getenv("SUPABASE_KEY", DEFAULT_SUPABASE_KEY)

class SupabaseClient:
    _instance = None

    def __init__(self) -> None:
        self.client: Optional[Any] = None
        self.session_file = os.path.join(DATA_DIR, "session.json")
        self._initialize()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SupabaseClient()
        return cls._instance

    def _initialize(self):
        """Initializes the Supabase client if credentials are available."""
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
                # Restore session if exists
                if os.path.exists(self.session_file):
                    with open(self.session_file, 'r') as f:
                        session = json.load(f)
                        self.client.auth.set_session(session["access_token"], session["refresh_token"])
            except Exception as e:
                logger.error(f"Supabase Init Failed: {e}")

    def login(self, email: str, password: str) -> bool:
        """Logs in to Supabase and saves session."""
        if not self.client:
            return False
        try:
            res = self.client.auth.sign_in_with_password({"email": email, "password": password})
            self._save_session(res.session)
            return True
        except Exception as e:
            logger.error(f"Login Failed: {e}")
            return False

    def _save_session(self, session: Any):
        """Saves session token to local file."""
        data = {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user": session.user.id
        }
        with open(self.session_file, 'w') as f:
            json.dump(data, f)

    def push_function(self, function_data: Dict[str, Any]) -> bool:
        """Pushes a function to the 'public_functions' table."""
        if not self.client:
            return False
            
        try:
            # Map local keys to Supabase schema
            # Assuming 'public_functions' table structure
            data = {
                "name": function_data.get("name"),
                "code": function_data.get("code"),
                "description": function_data.get("description"),
                "metadata": function_data.get("metadata", {}),
                "tags": function_data.get("tags", []),
                # "author_id" is handled by RLS/Auth default in Supabase usually, 
                # or we pass it if we are admin. For MVP, we let Supabase Auth handle it.
            }
            
            # Upsert based on name (if user owns it)
            # functionality depends on RLS policies
            self.client.table("public_functions").upsert(data, on_conflict="name").execute()
            return True
        except Exception as e:
            logger.error(f"Push to Cloud Failed: {e}")
            return False

    def search_public(self, query: str) -> List[Dict]:
        """Performs simple text search on public functions."""
        if not self.client:
            return []
        try:
            # Using Supabase's simple text search or just ILIKE for MVP
            res = self.client.table("public_functions").select("*").ilike("description", f"%{query}%").limit(5).execute()
            return res.data
        except Exception as e:
            logger.error(f"Public Search Failed: {e}")
            return []

supabase_client = SupabaseClient.get_instance()
