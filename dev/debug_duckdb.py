import os
import duckdb
import numpy as np
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "functions.duckdb")

print(f"Connecting to {DB_PATH}...")
con = duckdb.connect(DB_PATH)

print("\n--- Table Schema ---")
res = con.execute("DESCRIBE embeddings").fetchall()
for row in res:
    print(row)

print("\n--- Test Query (array_cosine_similarity) ---")
try:
    # Generate dummy vector
    vec = np.random.rand(1024).astype(np.float32).tolist()
    
    # Try with explicit cast to FLOAT[] (List) via parameter
    sql = "SELECT array_cosine_similarity(?::FLOAT[], ?::FLOAT[])"
    print(f"Testing SQL: {sql}")
    con.execute(sql, (vec, vec)).fetchall()
    print("SUCCESS: array_cosine_similarity(FLOAT[], FLOAT[]) worked.")
except Exception as e:
    print(f"FAILED: {e}")

print("\n--- Test Query (list_cosine_similarity) ---")
try:
    vec = np.random.rand(1024).astype(np.float32).tolist()
    sql = "SELECT list_cosine_similarity(?::FLOAT[], ?::FLOAT[])"
    print(f"Testing SQL: {sql}")
    con.execute(sql, (vec, vec)).fetchall()
    print("SUCCESS: list_cosine_similarity(FLOAT[], FLOAT[]) worked.")
except Exception as e:
    print(f"FAILED: {e}")

print("\n--- Test Query (Actual Table Usage) ---")
try:
    vec = np.random.rand(1024).astype(np.float32).tolist()
    # Try the query used in server.py
    sql = """
            SELECT 
                f.name,
                array_cosine_similarity(e.vector, ?::FLOAT[]) as score
            FROM embeddings e
            JOIN functions f ON e.function_id = f.id
            LIMIT 1
    """
    print("Testing Table Query (array_cosine_similarity)...")
    con.execute(sql, (vec,)).fetchall()
    print("SUCCESS: Table query worked.")
except Exception as e:
    print(f"FAILED: {e}")
    
    print("Retrying with list_cosine_similarity...")
    try:
        sql = """
                SELECT 
                    f.name,
                    list_cosine_similarity(e.vector, ?::FLOAT[]) as score
                FROM embeddings e
                JOIN functions f ON e.function_id = f.id
                LIMIT 1
        """
        con.execute(sql, (vec,)).fetchall()
        print("SUCCESS: Table query with list_cosine_similarity worked.")
    except Exception as e:
        print(f"FAILED AGAIN: {e}")

con.close()
