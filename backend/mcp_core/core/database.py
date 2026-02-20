import json
import logging
import os  # Added import for os module
import time

import duckdb
from mcp_core.core import config
from mcp_core.engine.embedding import embedding_service

try:
    import msvcrt

    _HAS_MSVCRT = True
except ImportError:
    _HAS_MSVCRT = False

import threading

logger = logging.getLogger(__name__)

LOCK_PATH = config.DATA_DIR / "functions.duckdb.lock"

# Thread lock to prevent intra-process contention before it hits the file system
_inner_lock = threading.Lock()


class DBWriteLock:
    """Cross-process file lock for DuckDB write operations on Windows."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._fp = None

    def __enter__(self):
        # logger.debug(f"DEBUG: Thread {threading.get_ident()} trying to acquire L-Lock")
        if not _inner_lock.acquire(timeout=self.timeout):
            logger.error(f"DEBUG: Thread {threading.get_ident()} TIMEOUT on L-Lock")
            raise TimeoutError("Could not acquire internal thread lock.")

        if not _HAS_MSVCRT:
            return self

        try:
            LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._fp = open(LOCK_PATH, "a")

            deadline = time.monotonic() + self.timeout
            while True:
                try:
                    msvcrt.locking(self._fp.fileno(), msvcrt.LK_NBLCK, 1)
                    # logger.debug(f"DEBUG: Thread {threading.get_ident()} acquired F-Lock")
                    return self
                except OSError:
                    if time.monotonic() > deadline:
                        raise TimeoutError(
                            "Could not acquire database lock. Another process (Cursor/Antigravity) "
                            "might be writing to Function Store. Please try again in a few seconds."
                        )
                    time.sleep(0.1)
        except Exception as e:
            _inner_lock.release()
            if isinstance(e, TimeoutError):
                raise
            raise RuntimeError(f"Lock initialization failed: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self._fp:
                try:
                    msvcrt.locking(self._fp.fileno(), msvcrt.LK_UNLCK, 1)
                    # logger.debug(f"DEBUG: Thread {threading.get_ident()} released F-Lock")
                except Exception:
                    pass
                finally:
                    self._fp.close()
                    self._fp = None
        finally:
            _inner_lock.release()
            # logger.debug(f"DEBUG: Thread {threading.get_ident()} released L-Lock")


def get_db_connection(read_only=False):
    """Gets a connection to the DuckDB database with retry logic for Windows lock contention."""
    max_retries = 10
    retry_delay = 0.2  # seconds

    last_err = None
    for attempt in range(max_retries):
        try:
            # Consistent path and config
            db_path = str(config.DB_PATH)
            if db_path != ":memory:":
                os.makedirs(os.path.dirname(db_path), exist_ok=True)

            conn = duckdb.connect(db_path, read_only=read_only)

            return conn
        except (duckdb.IOException, duckdb.Error) as e:
            last_err = e
            msg = str(e).lower()
            if (
                "process cannot access the file" in msg
                or "is in use" in msg
                or "locked" in msg
                or "already open" in msg
            ):
                time.sleep(retry_delay * (1.5**attempt))  # Exponential backoff
                continue
            raise

    logger.error(f"DuckDB Connection Failed after {max_retries} retries: {last_err}")
    raise last_err


def init_db():
    with DBWriteLock():
        conn = get_db_connection()
        try:
            # Create Sequence for ID
            conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_function_id START 1")
            conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_emb_id START 1")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS functions (
                    id INTEGER PRIMARY KEY DEFAULT nextval('seq_function_id'),
                    name VARCHAR,
                    code VARCHAR,
                    description VARCHAR,
                    tags VARCHAR,
                    metadata VARCHAR,
                    status VARCHAR DEFAULT 'active',
                    test_cases VARCHAR,
                    call_count INTEGER DEFAULT 0,
                    last_called_at VARCHAR,
                    created_at VARCHAR,
                    updated_at VARCHAR
                )
            """)

            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_functions_name ON functions (name)"
            )

            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY DEFAULT nextval('seq_emb_id'),
                    function_id INTEGER,
                    vector FLOAT[],
                    model_name VARCHAR,
                    dimension INTEGER,
                    encoded_at VARCHAR
                )
            """)

            # Config Table for Model Versioning
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key VARCHAR PRIMARY KEY,
                    value VARCHAR
                )
            """)

            # Migrations
            columns_res = conn.execute("DESCRIBE functions").fetchall()
            columns = [row[0] for row in columns_res]

            needed_cols = {
                "metadata": "NULL",
                "status": "'active'",
                "test_cases": "NULL",
                "call_count": "0",
                "last_called_at": "NULL",
            }

            for col, default_val in needed_cols.items():
                if col not in columns:
                    logger.info(f"Migrating DB: Adding '{col}' column.")
                    type_map = {"call_count": "INTEGER"}
                    col_type = type_map.get(col, "VARCHAR")
                    conn.execute(f"ALTER TABLE functions ADD COLUMN {col} {col_type}")
                    conn.execute(
                        f"UPDATE functions SET {col} = {default_val} WHERE {col} IS NULL"
                    )

            # No need to open new connections inside these helpers
            _check_model_version_internal(conn)
            recover_embeddings_internal(conn)

        finally:
            conn.close()


def recover_embeddings_internal(conn):
    """Checks for model or dimension mismatch and re-calculates embeddings if necessary."""
    try:
        current_model = embedding_service.model_name
        expected_dim = embedding_service.get_model_info()["dimension"]

        # 1. Find mismatched models, missing dimensions, or wrong dimensions
        rows = conn.execute(
            """
            SELECT f.id, f.name, f.description, f.tags, f.metadata, f.code, e.model_name, e.dimension
            FROM functions f
            JOIN embeddings e ON f.id = e.function_id
            WHERE e.model_name != ? OR e.dimension != ? OR e.dimension IS NULL
        """,
            (current_model, expected_dim),
        ).fetchall()

        if not rows:
            return

        logger.warning(
            f"Detected {len(rows)} inconsistent embeddings. Starting auto-recovery (Model: {current_model}, Dim: {expected_dim})..."
        )

        count = 0
        for row in rows:
            fid, name, desc, tags_json, meta_json, code, old_model, old_dim = row
            tags = json.loads(tags_json) if tags_json else []
            meta = json.loads(meta_json) if meta_json else {}
            deps = meta.get("dependencies", [])

            text_to_embed = f"Function Name: {name}\nDescription: {desc}\nTags: {', '.join(tags)}\nDependencies: {', '.join(deps)}\nCode:\n{code[:1000]}"

            try:
                embedding = embedding_service.get_embedding(text_to_embed)
                vector_list = embedding.tolist()

                conn.execute(
                    "UPDATE embeddings SET vector = ?, model_name = ?, dimension = ?, encoded_at = CURRENT_TIMESTAMP WHERE function_id = ?",
                    (vector_list, current_model, len(vector_list), fid),
                )
                count += 1
                if count % 5 == 0:
                    logger.info(f"Auto-recovery progress: {count}/{len(rows)}")
            except Exception as e:
                logger.error(f"Failed to recover embedding for '{name}': {e}")

        logger.info(f"Auto-recovery complete: Fixed {count} embeddings.")
        conn.commit()

    except Exception as e:
        logger.error(f"Error during embedding recovery: {e}")


def _check_model_version_internal(conn):
    """Checks if the current model version matches the database version, triggers migration if not."""
    try:
        row = conn.execute(
            "SELECT value FROM config WHERE key = 'embedding_model'"
        ).fetchone()
        current_model = embedding_service.model_name

        if not row:
            conn.execute(
                "INSERT INTO config (key, value) VALUES ('embedding_model', ?)",
                (current_model,),
            )
            conn.commit()
            return

        stored_model = row[0]
        if stored_model != current_model:
            logger.warning(
                f"Embedding model changed from '{stored_model}' to '{current_model}'. Migrating..."
            )
            conn.execute(
                "UPDATE config SET value = ? WHERE key = 'embedding_model'",
                (current_model,),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error checking model version: {e}")


# Public wrappers if needed
def recover_embeddings():
    with DBWriteLock():
        conn = get_db_connection()
        try:
            recover_embeddings_internal(conn)
        finally:
            conn.close()


def _check_model_version():
    with DBWriteLock():
        conn = get_db_connection()
        try:
            _check_model_version_internal(conn)
        finally:
            conn.close()
