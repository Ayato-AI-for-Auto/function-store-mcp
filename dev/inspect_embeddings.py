import duckdb
import os

db_path = r'c:/Users/saiha/My_Service/MCP/function_store_mcp/data/functions.duckdb'
output_file = 'inspect_embeddings.txt'

with open(output_file, 'w', encoding='utf-8') as f:
    if os.path.exists(db_path):
        try:
            conn = duckdb.connect(db_path, read_only=True)
            f.write(f"--- Embeddings Table ---\n")
            
            # Count
            count = conn.execute("SELECT COUNT(*) FROM embeddings").fetchall()[0][0]
            f.write(f"Row Count: {count}\n")
            
            # Schema
            cols = conn.execute("PRAGMA table_info('embeddings')").fetchall()
            f.write(f"Columns: {[c[1] for c in cols]}\n")
            
            # Check a sample text/metadata if available, to see what's being embedded
            # Assuming 'function_name' or 'text' column exists (standard for vector stores)
            col_names = [c[1] for c in cols]
            if 'function_name' in col_names:
                rows = conn.execute("SELECT function_name FROM embeddings LIMIT 10").fetchall()
                f.write(f"Sample Functions in Embeddings: {rows}\n")
                
        except Exception as e:
            f.write(f"Error: {e}\n")
    else:
        f.write("DB not found.\n")
