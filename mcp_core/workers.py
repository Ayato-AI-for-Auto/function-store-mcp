import os
import json
import logging
import threading
import atexit
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional
from mcp_core import config
from mcp_core.config import DATA_DIR
from mcp_core.database import get_db_connection, Database
from mcp_core.runtime import _run_test_cases
from mcp_core.environment import env_manager
from mcp_core.sync_engine import SyncEngine

logger = logging.getLogger(__name__)

class BackgroundVerifier:
    """Manages asynchronous verification of saved functions."""
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.stop_event = threading.Event()

    def start(self):
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _poll_loop(self):
        while not self.stop_event.is_set():
            try:
                conn = get_db_connection()
                pending = conn.execute("SELECT name, code, metadata, test_cases FROM functions WHERE status = 'pending'").fetchall()
                conn.close()
                for name, code, meta_json, tests_json in pending:
                    if self.stop_event.is_set():
                        break
                    meta = json.loads(meta_json) if meta_json else {}
                    tests = json.loads(tests_json) if tests_json else []
                    deps = meta.get("dependencies", [])
                    self._verify_task(name, code, deps, tests)
            except Exception as e:
                logger.error(f"Verifier Poll Error: {e}")
            
            # Use responsive wait
            if self.stop_event.wait(10):
                break

    def stop(self):
        self.stop_event.set()
        self.executor.shutdown(wait=False)

    def queue_verification(self, name: str, code: str, dependencies: List[str], test_cases: List[Dict]):
        self.executor.submit(self._verify_task, name, code, dependencies, test_cases)

    def _verify_task(self, name: str, code: str, dependencies: List[str], test_cases: List[Dict]):
        logger.info(f"Verifier: Starting task for '{name}'")
        python_exe, err = env_manager.get_python_executable(dependencies)
        if err:
            self._update_status(name, "failed", err)
            return
        passed, log = _run_test_cases(code, test_cases, python_exe)
        self._update_status(name, "active" if passed else "failed", log)

    def _update_status(self, name: str, status: str, log: str):
        conn = get_db_connection()
        try:
            conn.execute("UPDATE functions SET status = ?, updated_at = ? WHERE name = ?", (status, time.ctime(), name))
            conn.commit()
        finally:
            conn.close()

class SyncAgent:
    """Background service that synchronizes local functions with the Cloud Store."""
    def __init__(self, interval: Optional[int] = None):
        self.interval = interval or 300 # Poll every 5 minutes by default
        self.stop_event = threading.Event()
        self.thread = None
        self.sync_engine = SyncEngine(Database())

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)

    def _run_loop(self):
        while not self.stop_event.is_set():
            try:
                self._sync_pending()
            except Exception as e:
                logger.error(f"SyncAgent Sync Error: {e}")
            # Use wait() on stop_event for responsive shutdown
            self.stop_event.wait(self.interval)

    def _sync_pending(self):
        """Pulls from cloud and pushes local changes."""
        if not self.sync_engine.is_connected():
            return
            
        logger.info("SyncAgent: Starting sync check...")
        
        # 1. Pull from cloud to local
        cloud_funcs = self.sync_engine.pull_functions()
        db = Database()
        for cf in cloud_funcs:
            db.upsert_function_from_cloud(cf)
            
        # 2. Push local functions to cloud (active ones that are not already synced)
        conn = get_db_connection()
        try:
            # We iterate through all 'active' functions. 
            # In a more advanced version, we'd use a 'last_synced_at' marker.
            local_funcs = conn.execute("SELECT name, code, description, tags, metadata, version FROM functions WHERE sync_status = 'pending'").fetchall()
            for name, code, desc, tags_json, meta_json, ver in local_funcs:
                if self.stop_event.is_set():
                    break
                tags = json.loads(tags_json) if tags_json else []
                meta = json.loads(meta_json) if meta_json else {}
                
                # Push will upsert on Supabase side based on (team_id, name)
                self.sync_engine.push_function({
                    "name": name,
                    "code": code,
                    "description": desc,
                    "tags": tags,
                    "metadata": meta,
                    "version": ver
                })
        finally:
            conn.close()

class DashboardExporter:
    """Periodically exports the 'functions' table to a Parquet file."""
    def __init__(self, interval: int = 2):
        self.interval = interval
        self.stop_event = threading.Event()
        self.thread = None
        self.parquet_path = os.path.join(DATA_DIR, "dashboard.parquet")

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)

    def _run_loop(self):
        while not self.stop_event.is_set():
            self._export_parquet()
            self.stop_event.wait(self.interval)

    def _export_parquet(self):
        try:
            conn = get_db_connection()
            conn.execute(f"COPY (SELECT * FROM functions) TO '{self.parquet_path}' (FORMAT PARQUET)")
            conn.close()
        except Exception:
            pass

class TranslationWorker:
    """Manages asynchronous translation using TranslateGemma."""
    def __init__(self):
        self.stop_event = threading.Event()
        self.interval = 15 # Poll every 15 seconds
        self.threads = []

    def start(self):
        self.stop_event.clear()
        t1 = threading.Thread(target=self._startup_sweep, daemon=True)
        t2 = threading.Thread(target=self._poll_loop, daemon=True)
        t1.start()
        t2.start()
        self.threads = [t1, t2]

    def stop(self):
        self.stop_event.set()
        for t in self.threads:
            t.join(timeout=1)

    def _startup_sweep(self):
        logger.info("TranslationWorker: Starting startup sweep for missing translations...")
        self._process_pending_translations()

    def _poll_loop(self):
        while not self.stop_event.is_set():
            # Wait for interval or stop event
            if self.stop_event.wait(self.interval):
                break
            try:
                if not config.FS_ENABLE_TRANSLATION:
                    continue
                self._process_pending_translations()
            except Exception as e:
                logger.error(f"TranslationWorker Poll Error: {e}")

    def _process_pending_translations(self):
        conn = get_db_connection()
        try:
            # Find functions missing one of the localized descriptions
            pending = conn.execute(
                "SELECT name, description, description_en, description_jp FROM functions WHERE description_en IS NULL OR description_jp IS NULL"
            ).fetchall()
        finally:
            conn.close()

        if not pending:
            return

        from mcp_core.translation import translation_service
        for name, desc, desc_en, desc_jp in pending:
            if self.stop_event.is_set():
                break
            logger.info(f"TranslationWorker: Processing '{name}'")
            new_en, new_jp = translation_service.ensure_bilingual(desc, desc_en, desc_jp)
            
            # Update only if translation actually happened
            if new_en != desc_en or new_jp != desc_jp:
                translation_service.update_function_descriptions(name, new_en, new_jp)

background_verifier = BackgroundVerifier()
translation_worker = TranslationWorker()
sync_agent = SyncAgent()
dashboard_exporter = DashboardExporter()

# atexit.register(docker_runtime.cleanup)
atexit.register(sync_agent.stop)
atexit.register(dashboard_exporter.stop)
atexit.register(translation_worker.stop)
atexit.register(background_verifier.stop)
