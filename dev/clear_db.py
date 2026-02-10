import duckdb
import time
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "functions.duckdb")

print(f"Connecting to {DB_PATH}...")
try:
    con = duckdb.connect(DB_PATH)
    
    print("Clearing incompatible embeddings...")
    con.execute("DELETE FROM embeddings")
    count = con.execute("SELECT count(*) FROM embeddings").fetchone()[0]
    print(f"Embeddings count after delete: {count}")
    
    print("Clearing functions to ensure fresh start (optional, but cleaner for test)...")
    con.execute("DELETE FROM functions")
    f_count = con.execute("SELECT count(*) FROM functions").fetchone()[0]
    print(f"Functions count after delete: {f_count}")
    
    con.close()
    print("SUCCESS: Database cleared.")
except Exception as e:
    print(f"FAILED: {e}")
