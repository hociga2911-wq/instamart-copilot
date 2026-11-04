

from pathlib import Path
import sqlite3
import pandas as pd

CLEAN_DIR = Path("data/clean")
DB_PATH = Path("data/instamart.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Required tables use the filenames specified by the mentor.
tables = {
    "customers": "customers.csv",
    "products": "products.csv",
    "orders": "orders.csv",
}

print("========== INSTMART DATABASE CREATION ==========")

with sqlite3.connect(DB_PATH) as conn:
    for table_name, filename in tables.items():
        file_path = CLEAN_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Required clean CSV not found: {file_path}"
            )

        df = pd.read_csv(file_path)

        # Keep order timestamps in YYYY-MM-DD HH:MM:SS text format.
        if table_name == "orders":
            df["order_ts"] = pd.to_datetime(
                df["order_ts"], errors="raise"
            ).dt.strftime("%Y-%m-%d %H:%M:%S")

        df.to_sql(
            table_name,
            conn,
            if_exists="replace",
            index=False,
        )

        print(f"{table_name}: {len(df)} records inserted")

    # Add indexes to speed up common joins.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_customer "
        "ON orders(customer_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_product "
        "ON orders(product_id)"
    )

    conn.commit()

    print("\n========== DATABASE VERIFICATION ==========")

    expected_counts = {
        "customers": 1200,
        "products": 40,
        "orders": 12309,
    }

    for table_name, expected_count in expected_counts.items():
        actual_count = conn.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        ).fetchone()[0]

        print(f"{table_name}: {actual_count} records")

        if actual_count != expected_count:
            raise AssertionError(
                f"{table_name}: expected {expected_count}, "
                f"found {actual_count}"
            )

    # Verify that no pending orders remain.
    pending_count = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE status = 'pending'"
    ).fetchone()[0]

    if pending_count != 0:
        raise AssertionError(
            f"Expected 0 pending orders, found {pending_count}"
        )

    print("Required table counts and order statuses verified.")

print("\nDatabase created successfully!")
print("Location:", DB_PATH.resolve())
