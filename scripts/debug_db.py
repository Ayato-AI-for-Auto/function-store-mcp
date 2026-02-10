import duckdb
import pathlib

p = pathlib.Path('data/functions.duckdb')
if not p.exists():
    print("DB does not exist")
    exit(1)

conn = duckdb.connect(str(p))
try:
    rows = conn.execute("SELECT name, description_en, description_jp FROM functions").fetchall()
    for row in rows:
        print(f"Name: {row[0]}")
        print(f"  EN: {row[1]}")
        print(f"  JP: {row[2]}")
finally:
    conn.close()
