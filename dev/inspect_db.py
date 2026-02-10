import duckdb
import sqlite3
import os
import pprint

output_file = 'inspect_output.txt'

with open(output_file, 'w', encoding='utf-8') as f:
    # 1. Inspect Function Store DuckDB
    db_path = 'data/functions.duckdb'
    f.write(f"\nDistilling Truth from: {db_path}\n{'='*30}\n")
    
    if os.path.exists(db_path):
        try:
            conn = duckdb.connect(db_path, read_only=True)
            tables = conn.execute("SHOW TABLES").fetchall()
            f.write(f"Tables: {[t[0] for t in tables]}\n")
            
            # Check functions table
            if any(t[0] == 'functions' for t in tables):
                count = conn.execute("SELECT COUNT(*) FROM functions").fetchall()[0][0]
                f.write(f"Total Functions: {count}\n")
                
                rows = conn.execute("SELECT name, tags, execution_mode FROM functions").fetchall()
                for row in rows:
                    f.write(f"[FUNC] {row[0]} | Tags: {row[1]} | Mode: {row[2]}\n")
            else:
                f.write("Table 'functions' NOT FOUND.\n")
                
        except Exception as e:
            f.write(f"DuckDB Error: {e}\n")
    else:
        f.write("Function Store DB not found.\n")

    # 2. Inspect Agent SQLite DB
    agent_db_path = '../Original_AI/sovereign-mvp/agent.db' # Relative path
    f.write(f"\nDistilling Truth from: {agent_db_path}\n{'='*30}\n")
    
    if os.path.exists(agent_db_path):
        try:
            conn = sqlite3.connect(agent_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            f.write(f"Tables: {[t[0] for t in tables]}\n")
            
            # Check for any stored code or similar?
            # Usually agent.db stores logs/state.
            
        except Exception as e:
            f.write(f"SQLite Error: {e}\n")
    else:
        f.write("Agent DB not found.\n")
