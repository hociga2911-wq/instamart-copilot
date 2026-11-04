from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
DB = ROOT / "data" / "instamart.db"

checks = []

def check(description, condition):
    assert condition, f"FAILED: {description}"
    checks.append(description)
    print(f"PASS: {description}")

customers = pd.read_csv(CLEAN / "customers.csv")
products = pd.read_csv(CLEAN / "products.csv")
orders = pd.read_csv(CLEAN / "orders.csv")

check("Customer row count is 1200", len(customers) == 1200)
check("Customer IDs are unique", customers["customer_id"].is_unique)
check("Customer ages have no missing values", customers["age"].notna().all())
check("Customer ages are within 10-100", customers["age"].between(10, 100).all())
check("Customer cities are the six normalized cities",
      set(customers["city"].unique()) ==
      {"Pune", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Mumbai"})
check("Customer genders are normalized",
      set(customers["gender"].unique()) <= {"female", "male", "unknown"})
check("Product row count is 40", len(products) == 40)
check("Product IDs are unique", products["product_id"].is_unique)
check("Order row count is 12309", len(orders) == 12309)
check("Order IDs are unique", orders["order_id"].is_unique)
check("No pending orders remain", not orders["status"].eq("pending").any())
check("Order statuses are completed or cancelled",
      set(orders["status"].unique()) <= {"completed", "cancelled"})
check("All order amounts are numeric and present",
      pd.to_numeric(orders["order_amount"], errors="coerce").notna().all())
check("No negative delivery times remain",
      not pd.to_numeric(orders["delivery_minutes"], errors="coerce").lt(0).any())
check("Cancelled orders have missing delivery times",
      orders.loc[orders["status"].eq("cancelled"), "delivery_minutes"].isna().all())
check("Completed orders have delivery times",
      pd.to_numeric(
          orders.loc[orders["status"].eq("completed"), "delivery_minutes"],
          errors="coerce"
      ).notna().all())
check("Completed orders count is 11110",
      int(orders["status"].eq("completed").sum()) == 11110)
check("Cancelled orders count is 1199",
      int(orders["status"].eq("cancelled").sum()) == 1199)

with sqlite3.connect(DB) as conn:
    tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    check("Database contains customers, products, and orders",
          {"customers", "products", "orders"} <= tables)

    db_counts = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("customers", "products", "orders")
    }
    check("Database table counts match cleaned CSVs",
          db_counts == {
              "customers": len(customers),
              "products": len(products),
              "orders": len(orders),
          })

    revenue = conn.execute(
        "SELECT ROUND(SUM(order_amount), 2) FROM orders "
        "WHERE status = 'completed'"
    ).fetchone()[0]
    check("Completed revenue is INR 2998668.80",
          abs(revenue - 2998668.80) < 0.01)

print(f"\n{len(checks)} CHECKPOINTS PASSED")
print("ALL CHECKPOINTS PASSED")
