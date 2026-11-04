


from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "instamart.db"
SQL_FILE = ROOT / "sql" / "queries.sql"

if not DB_PATH.exists():
    raise FileNotFoundError(f"Database not found: {DB_PATH}")

if not SQL_FILE.exists():
    raise FileNotFoundError(f"SQL file not found: {SQL_FILE}")

sql_text = SQL_FILE.read_text(encoding="utf-8")
queries = [q.strip() for q in sql_text.split(";") if q.strip()]

if len(queries) != 7:
    raise ValueError(f"Expected 7 queries, found {len(queries)}")

with sqlite3.connect(DB_PATH) as conn:
    print(f"Database: {DB_PATH}")
    print(f"Queries found: {len(queries)}")

    for i, query in enumerate(queries, start=1):
        result = pd.read_sql_query(query, conn)
        print(f"\nQUERY {i}")
        print("-" * 60)
        print(f"Rows returned: {len(result)}")
        print(result.to_string(index=False))

print("\nSQL ANALYSIS COMPLETED")
