import json
import logging
import os  # Added import for os module

import duckdb
from mcp_core.core import config
from mcp_core.engine.embedding import embedding_service

logger = logging.getLogger(__name__)


def get_db_connection(read_only=False):
    """Gets a connection to the DuckDB database with retry logic for Windows lock contention."""
    import time

    max_retries = 10
    retry_delay = 0.2  # seconds

    last_err = None
    for attempt in range(max_retries):
        try:
            # Consistent path and config
            db_path = str(config.DB_PATH)
            if db_path != ":memory:":
                os.makedirs(os.path.dirname(db_path), exist_ok=True)

            # DuckDB allows multiple connections to the same file in the SAME process
            # if they share the same configuration. We use defaults.
            conn = duckdb.connect(db_path, read_only=read_only)
            return conn
        except (duckdb.IOException, duckdb.Error) as e:
            last_err = e
            # Windows sharing violation or DuckDB lock
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
    conn = get_db_connection()
    try:
        # Create Sequence for ID
        conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_function_id START 1")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_version_id START 1")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_emb_id START 1")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS functions (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_function_id'),
                name VARCHAR,
                code VARCHAR,
                description VARCHAR,
                description_en VARCHAR,
                description_jp VARCHAR,
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

        # Removing FOREIGN KEY constraints to avoid DuckDB ConstraintException clashing in transactions.
        # Integrity is managed at the application level in logic.py.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_emb_id'),
                function_id INTEGER,
                vector FLOAT[],
                model_name VARCHAR
            )
        """)

        # Version History Table (Removed FK for robust deletion)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS function_versions (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_version_id'),
                function_id INTEGER,
                version INTEGER,
                code VARCHAR,
                dependencies VARCHAR,
                test_cases VARCHAR,
                description VARCHAR,
                description_en VARCHAR,
                description_jp VARCHAR,
                archived_at VARCHAR
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
            "version": "'1'",
            "description_en": "NULL",
            "description_jp": "NULL",
            "call_count": "0",
            "last_called_at": "NULL",
        }

        for col, default_val in needed_cols.items():
            if col not in columns:
                logger.info(f"Migrating DB: Adding '{col}' column.")
                type_map = {"call_count": "INTEGER", "version": "INTEGER"}
                col_type = type_map.get(col, "VARCHAR")
                conn.execute(f"ALTER TABLE functions ADD COLUMN {col} {col_type}")
                conn.execute(
                    f"UPDATE functions SET {col} = {default_val} WHERE {col} IS NULL"
                )

        # Migrations for embeddings table
        emb_cols_res = conn.execute("DESCRIBE embeddings").fetchall()
        emb_cols = [row[0] for row in emb_cols_res]
        if "model_name" not in emb_cols:
            logger.info("Migrating DB: Adding 'model_name' column to embeddings table.")
            conn.execute("ALTER TABLE embeddings ADD COLUMN model_name VARCHAR")
        if "dimension" not in emb_cols:
            logger.info("Migrating DB: Adding 'dimension' column to embeddings table.")
            conn.execute("ALTER TABLE embeddings ADD COLUMN dimension INTEGER")
        if "encoded_at" not in emb_cols:
            logger.info("Migrating DB: Adding 'encoded_at' column to embeddings table.")
            conn.execute("ALTER TABLE embeddings ADD COLUMN encoded_at VARCHAR")

            # Automatic Migration: Re-calculate embeddings for legacy records using CURRENT model
            logger.info(
                f"Migrating DB: Re-calculating legacy embeddings using current model '{config.EMBEDDING_MODEL_ID}'..."
            )

            legacy_rows = conn.execute("""
                SELECT f.id, f.name, f.description, f.tags, f.metadata, f.code 
                FROM functions f 
                JOIN embeddings e ON f.id = e.function_id 
                WHERE e.model_name IS NULL
            """).fetchall()

            count = 0
            for row in legacy_rows:
                fid, name, desc, tags_json, meta_json, code = row
                tags = json.loads(tags_json) if tags_json else []
                meta = json.loads(meta_json) if meta_json else {}
                deps = meta.get("dependencies", [])

                text_to_embed = f"Function Name: {name}\nDescription: {desc}\nTags: {', '.join(tags)}\nDependencies: {', '.join(deps)}\nCode:\n{code[:1000]}"

                try:
                    embedding = embedding_service.get_embedding(text_to_embed)
                    vector_list = embedding.tolist()

                    conn.execute(
                        "UPDATE embeddings SET vector = ?, model_name = ?, dimension = ?, encoded_at = CURRENT_TIMESTAMP WHERE function_id = ?",
                        (vector_list, config.EMBEDDING_MODEL_ID, len(vector_list), fid),
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to re-embed '{name}' during migration: {e}")

            logger.info(f"Migration Complete: Re-embedded {count} functions.")

        # Check for model/dimension mismatch and recover
        recover_embeddings()

    finally:
        conn.close()


def recover_embeddings():
    """Checks for model or dimension mismatch and re-calculates embeddings if necessary."""
    conn = get_db_connection()
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
    finally:
        conn.close()


def _check_model_version():
    """Checks if the current model version matches the database version, triggers migration if not."""
    conn = get_db_connection()
    try:
        # Get stored model version
        row = conn.execute(
            "SELECT value FROM config WHERE key = 'embedding_model'"
        ).fetchone()
        current_model = embedding_service.model_name

        if not row:
            # First run or direct migration
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
            # Here we would trigger a full re-embedding if needed, but for now we just update config
            # and let the init_db migration handle NULL model_name entries.
            conn.execute(
                "UPDATE config SET value = ? WHERE key = 'embedding_model'",
                (current_model,),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error checking model version: {e}")
    finally:
        conn.close()
