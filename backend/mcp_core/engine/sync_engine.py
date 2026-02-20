import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from mcp_core.core import config
from mcp_core.core.database import DBWriteLock, get_db_connection

logger = logging.getLogger(__name__)


class GitHubSyncEngine:
    """
    Sync Engine that treats a GitHub Public Repository as a Serverless Database.
    Tasks:
    1. Clone/Pull from the Hub.
    2. Import JSON data into Local DuckDB.
    3. Export Local changes to JSON and Push to Hub.
    """

    def __init__(self):
        self.repo_url = config.SYNC_REPO_URL
        self.local_dir = config.SYNC_LOCAL_DIR
        self.functions_dir = self.local_dir / "functions"
        self._initialized = False

    def _run_git(self, args: List[str], cwd: Optional[Path] = None) -> bool:
        """Helper to run git commands."""
        try:
            cmd = ["git"] + args
            subprocess.run(
                cmd,
                cwd=str(cwd or self.local_dir),
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.cmd} -> {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error running git: {e}")
            return False

    def ensure_repo(self) -> bool:
        """Ensures the local cache directory is a valid git repository."""
        if not (self.local_dir / ".git").exists():
            logger.info(f"Sync: Initializing local hub cache at {self.local_dir}...")
            # If directory is not empty but no .git, it's a conflict, but we assume it's clean for now
            if self._run_git(["clone", "--depth", "1", self.repo_url, "."]):
                self._initialized = True
            else:
                # If clone fails (e.g. repo empty), try init
                if self._run_git(["init"]):
                    self._run_git(["remote", "add", "origin", self.repo_url])
                    self._initialized = True
        else:
            self._initialized = True

        if self._initialized:
            self.functions_dir.mkdir(parents=True, exist_ok=True)

        return self._initialized

    def pull(self) -> int:
        """Fetch latest from Hub and merge into local DB."""
        if not self.ensure_repo():
            return 0

        logger.info("Sync: Pulling latest changes from Hub...")
        if not self._run_git(["pull", "origin", "main"]):
            logger.warning("Sync: Pull failed (likely empty repository or conflict).")
            # Don't return, we try to parse what we have

        count = 0
        if not self.functions_dir.exists():
            return 0

        with DBWriteLock():
            conn = get_db_connection()
            try:
                for json_file in self.functions_dir.glob("*.json"):
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        name = data.get("name")
                        if not name:
                            continue

                        # If code or description changed, update
                        res = conn.execute(
                            "SELECT code, description FROM functions WHERE name = ?",
                            (name,),
                        ).fetchone()
                        if (
                            not res
                            or res[0] != data.get("code")
                            or res[1] != data.get("description")
                        ):
                            logger.info(f"Sync: Updating '{name}' (detected changes)")
                            self._upsert_function(conn, data)
                            count += 1
                    except Exception as fe:
                        logger.error(f"Sync: Failed to parse {json_file.name}: {fe}")
                conn.commit()
            finally:
                conn.close()

        logger.info(f"Sync: Pull complete. Updated {count} functions.")
        return count

    def _upsert_function(self, conn, data: Dict):
        """Helper to upsert function data into DuckDB."""
        # This is a simplified version of logic.py's save.
        # In a real system, we'd share the same save logic.
        from datetime import datetime

        now = datetime.now().isoformat()

        # Check if exists
        row = conn.execute(
            "SELECT id FROM functions WHERE name = ?", (data["name"],)
        ).fetchone()

        tags_json = json.dumps(data.get("tags", []))
        metadata = {
            "dependencies": data.get("dependencies", []),
            "quality_score": data.get("quality_score", 0),
            "sync_source": "github-hub",
        }
        meta_json = json.dumps(metadata)

        if row:
            fid = row[0]
            conn.execute(
                """
                UPDATE functions SET 
                    code = ?, description = ?, 
                    tags = ?, metadata = ?, updated_at = ?
                WHERE id = ?
            """,
                (
                    data["code"],
                    data.get("description", ""),
                    tags_json,
                    meta_json,
                    now,
                    fid,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO functions (name, code, description, tags, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data["name"],
                    data["code"],
                    data.get("description", ""),
                    tags_json,
                    meta_json,
                    now,
                    now,
                ),
            )

    def push(self, name: str) -> bool:
        """Export a local function to the Hub cache and push."""
        if not self.ensure_repo():
            return False

        logger.info(f"Sync: Pushing '{name}' to Hub...")
        conn = get_db_connection(read_only=False)
        try:
            if not self._export_to_cache(conn, name):
                logger.error(f"Sync: Function '{name}' not found locally.")
                return False

            # Commit and push
            self._run_git(["add", f"functions/{name}.json"])

            # --- Index update ---
            self._update_index()
            self._run_git(["add", "index.json"])

            # Check if there are changes to commit
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.local_dir),
                capture_output=True,
                text=True,
            )
            if not status.stdout.strip():
                logger.info(f"Sync: No changes to push for '{name}'.")
                return True

            self._run_git(["commit", "-m", f"feat: sync {name}"])
            return self._run_git(["push", "origin", "main"])

        finally:
            conn.close()

    def publish_all(self):
        """Export all local functions to the Hub and push in a single batch."""
        if not self.ensure_repo():
            return False

        logger.info("Sync: Publishing all local functions to Hub...")
        conn = get_db_connection(read_only=False)
        try:
            rows = conn.execute(
                "SELECT name FROM functions WHERE status != 'deleted'"
            ).fetchall()
            for r in rows:
                name = r[0]
                self._export_to_cache(conn, name)

            self._update_index()
            self._run_git(["add", "functions/*.json", "index.json"])
            self._run_git(["commit", "-m", "feat: bulk publish all functions"])
            return self._run_git(["push", "origin", "main"])
        finally:
            conn.close()

    def _export_to_cache(self, conn, name: str) -> bool:
        """Helper to export a single function to the local cache dir."""
        row = conn.execute(
            """
            SELECT name, code, description, tags, metadata, test_cases 
            FROM functions WHERE name = ?
        """,
            (name,),
        ).fetchone()
        if not row:
            return False

        # row indices: 0=name, 1=code, 2=description, 3=tags, 4=metadata, 5=test_cases
        meta = json.loads(row[4]) if row[4] else {}
        data = {
            "name": row[0],
            "code": row[1],
            "description": row[2],
            "tags": json.loads(row[3]) if row[3] else [],
            "test_cases": json.loads(row[5]) if row[5] else [],
            "dependencies": meta.get("dependencies", []),
            "quality_score": meta.get("quality_score", 0),
            "updated_at": datetime.now().isoformat(),
        }

        fpath = self.functions_dir / f"{name}.json"
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True

    def _update_index(self):
        """Generates a lightweight index.json for all functions in the hub."""
        index = []
        for fpath in self.functions_dir.glob("*.json"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                index.append(
                    {
                        "name": data["name"],
                        "description": data.get("description", ""),
                        "tags": data.get("tags", []),
                    }
                )
            except Exception as e:
                logger.error(f"Sync: Failed to parse {fpath.name} for index: {e}")
                continue

        with open(self.local_dir / "index.json", "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)


# Singleton Instance
sync_engine = GitHubSyncEngine()
