import logging
import json
from typing import List
from mcp_core.database import Database, get_db_connection
from mcp_core.supabase_client import supabase_client

logger = logging.getLogger("mcp_core.sync")

class SyncEngine:
    def __init__(self, db: Database):
        self.db = db
        self.client = supabase_client

    def is_connected(self) -> bool:
        return self.client.client is not None

    def sync_to_public(self):
        """Pushes all local 'active' functions to the public cloud."""
        if not self.is_connected():
            return

        conn = get_db_connection()
        try:
            # Select all active functions
            local_funcs = conn.execute(
                "SELECT name, code, description, tags, metadata, version FROM functions WHERE status = 'active' OR status = 'verified'"
            ).fetchall()
            
            success_count = 0
            for name, code, desc, tags_json, meta_json, ver in local_funcs:
                tags = json.loads(tags_json) if tags_json else []
                meta = json.loads(meta_json) if meta_json else {}
                
                payload = {
                    "name": name,
                    "code": code,
                    "description": desc,
                    "tags": tags,
                    "metadata": meta,
                    "version": ver
                }
                
                if self.client.push_function(payload):
                    success_count += 1
            
            if success_count > 0:
                logger.info(f"Public Sync: Pushed {success_count} functions to cloud.")
                
        except Exception as e:
            logger.error(f"Sync Error: {e}")
        finally:
            conn.close()

    def push_function(self, func_data: dict):
        """Wrapper for direct push."""
        return self.client.push_function(func_data)

    def pull_functions(self) -> List[dict]:
        """Not implemented for Public MVP yet."""
        return []

    def sync_all(self):
        """For MVP, just push to public."""
        self.sync_to_public()
