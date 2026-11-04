from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "instamart.db"
OUT = ROOT / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

with sqlite3.connect(DB_PATH) as conn:
    orders = pd.read_sql_query(
        "SELECT * FROM orders WHERE status = 'completed'", conn
    )
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    products = pd.read_sql_query("SELECT * FROM products", conn)

orders["order_amount"] = pd.to_numeric(orders["order_amount"], errors="coerce")
orders["discount_pct"] = pd.to_numeric(orders["discount_pct"], errors="coerce")
orders["quantity"] = pd.to_numeric(orders["quantity"], errors="coerce")
orders["delivery_minutes"] = pd.to_numeric(
    orders["delivery_minutes"], errors="coerce"
)

# 1. Revenue pivot by city and product category, including grand totals
joined = (
    orders.merge(customers[["customer_id", "city"]], on="customer_id", how="left")
    .merge(products[["product_id", "category"]], on="product_id", how="left")
)

pivot = pd.pivot_table(
    joined,
    index="city",
    columns="category",
    values="order_amount",
    aggfunc="sum",
    fill_value=0,
    margins=True,
    margins_name="Grand Total",
)

pivot.to_csv(OUT / "revenue_pivot.csv")
print("\n=== REVENUE PIVOT (with grand totals) ===")
print(pivot.to_string())

# 2. Named aggregation per city
city_summary = joined.groupby("city").agg(
    total_revenue=("order_amount", "sum"),
    mean_order_amount=("order_amount", "mean"),
    order_count=("order_id", "count"),
).reset_index()

city_summary.to_csv(OUT / "city_summary.csv", index=False)
print("\n=== CITY SUMMARY ===")
print(city_summary.round(2).to_string(index=False))

# 3. Completed order amount distribution and IQR outliers
amount = orders["order_amount"].dropna()
q1 = amount.quantile(0.25)
median = amount.median()
q3 = amount.quantile(0.75)
iqr = q3 - q1
lower_fence = q1 - 1.5 * iqr
upper_fence = q3 + 1.5 * iqr
below = int((amount < lower_fence).sum())
above = int((amount > upper_fence).sum())

distribution = pd.DataFrame([{
    "count": int(amount.count()),
    "mean": amount.mean(),
    "median": median,
    "skewness": amount.skew(),
    "Q1": q1,
    "Q3": q3,
    "IQR": iqr,
    "lower_fence": lower_fence,
    "upper_fence": upper_fence,
    "outliers_below": below,
    "outliers_above": above,
}])

distribution.to_csv(OUT / "order_amount_distribution.csv", index=False)
print("\n=== ORDER AMOUNT DISTRIBUTION ===")
print(distribution.round(2).to_string(index=False))

# 4. Correlation matrix
corr_cols = [
    "order_amount",
    "discount_pct",
    "quantity",
    "delivery_minutes",
]
correlation = orders[corr_cols].corr()
correlation.to_csv(OUT / "correlation_matrix.csv")
print("\n=== CORRELATION MATRIX ===")
print(correlation.round(4).to_string())

pairs = correlation.where(
    pd.DataFrame(
        [[i != j for j in corr_cols] for i in corr_cols],
        index=corr_cols,
        columns=corr_cols,
    )
).stack()
strongest_pair = pairs.abs().idxmax()
print(
    "\nLargest absolute correlation:",
    strongest_pair[0], "vs", strongest_pair[1],
    f"({pairs.loc[strongest_pair]:.4f})"
)

print(f"\nAnalysis CSVs saved in: {OUT}")
