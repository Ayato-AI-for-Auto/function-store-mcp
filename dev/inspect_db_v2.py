import duckdb
import sqlite3
import os
import pprint

output_file = 'inspect_output_v2.txt'

with open(output_file, 'w', encoding='utf-8') as f:
    # 1. Inspect Function Store DuckDB (Absolute Path)
    db_path = r'c:/Users/saiha/My_Service/MCP/function_store_mcp/data/functions.duckdb'
    f.write(f"\nDistilling Truth from: {db_path}\n{'='*30}\n")
    
    if os.path.exists(db_path):
        try:
            conn = duckdb.connect(db_path, read_only=True)
            tables = conn.execute("SHOW TABLES").fetchall()
            f.write(f"Tables: {[t[0] for t in tables]}\n")
            
            if any(t[0] == 'functions' for t in tables):
                # Inspect schema
                columns = conn.execute("PRAGMA table_info('functions')").fetchall()
                col_names = [c[1] for c in columns]
                f.write(f"Columns: {col_names}\n")
                
                count = conn.execute("SELECT COUNT(*) FROM functions").fetchall()[0][0]
                f.write(f"Total Functions: {count}\n")
                
                # Safe query
                select_cols = ['name', 'tags']
                if 'description' in col_names: select_cols.append('description')
                
                query = f"SELECT {', '.join(select_cols)} FROM functions"
                rows = conn.execute(query).fetchall()
                for row in rows:
                    f.write(f"[FUNC] {row}\n")
            else:
                f.write("Table 'functions' NOT FOUND.\n")
                
        except Exception as e:
            f.write(f"DuckDB Error: {e}\n")
    else:
        f.write("Function Store DB not found.\n")

    # 2. Inspect Agent SQLite DB (Absolute Path)
    agent_db_path = r'c:/Users/saiha/My_Service/Original_AI/sovereign-mvp/agent.db'
    f.write(f"\nDistilling Truth from: {agent_db_path}\n{'='*30}\n")
    
    if os.path.exists(agent_db_path):
        try:
            conn = sqlite3.connect(agent_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            f.write(f"Tables: {[t[0] for t in tables]}\n")
            
            for table in tables:
                t_name = table[0]
                cursor.execute(f"PRAGMA table_info({t_name})")
                cols = [info[1] for info in cursor.fetchall()]
                cursor.execute(f"SELECT COUNT(*) FROM {t_name}")
                cnt = cursor.fetchone()[0]
                f.write(f"Table: {t_name} | Count: {cnt} | Cols: {cols}\n")
                
        except Exception as e:
            f.write(f"SQLite Error: {e}\n")
    else:
        f.write("Agent DB not found.\n")
