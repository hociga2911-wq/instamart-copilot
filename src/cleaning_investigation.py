
from pathlib import Path
import pandas as pd

RAW = Path("data/raw")

customers = pd.read_csv(RAW / "customers.csv")
orders = pd.read_csv(RAW / "orders.csv")

print("\n===== 1. INVALID CUSTOMER AGES =====")

invalid_ages = customers[
    customers["age"].notna()
    & ((customers["age"] < 18) | (customers["age"] > 100))
]

print(invalid_ages[["customer_id", "age"]].to_string(index=False))
print("Invalid age count:", len(invalid_ages))

print("\n===== 2. INVALID ORDER AMOUNTS =====")

amount = pd.to_numeric(orders["order_amount"], errors="coerce")

invalid_amounts = orders[amount.isna()]

print("Invalid amount count:", len(invalid_amounts))
print("\nOriginal amount values:")
print(invalid_amounts["order_amount"].value_counts(dropna=False).to_string())

print("\nSample affected orders:")
print(
    invalid_amounts[
        ["order_id", "customer_id", "status", "order_amount"]
    ].head(15).to_string(index=False)
)

print("\n===== 3. NEGATIVE DELIVERY TIMES =====")

negative_delivery = orders[orders["delivery_minutes"] < 0]

print(
    negative_delivery[
        ["order_id", "status", "delivery_minutes"]
    ].to_string(index=False)
)

print("\n===== 4. REPEATED ORDER IDS =====")

id_counts = orders["order_id"].value_counts()

repeated_ids = id_counts[id_counts > 1]

print("Repeated order ID count:", len(repeated_ids))
print("Rows belonging to repeated IDs:", int(repeated_ids.sum()))
print("\nMost repeated IDs:")
print(repeated_ids.head(15).to_string())

print("\n===== 5. STATUS AND DELIVERY ANALYSIS =====")

print(
    orders.groupby("status")["delivery_minutes"]
    .agg(["count", "mean", "min", "max"])
    .to_string()
)




print("\n===== 6. CORRECT STATUS COUNTS =====")

print("\nTotal rows by status:")
print(orders["status"].value_counts(dropna=False))

print("\nStatus and delivery-time summary:")
print(
    orders.groupby("status", dropna=False)
    .agg(
        total_rows=("order_id", "size"),
        valid_delivery_times=("delivery_minutes", "count"),
        missing_delivery_times=("delivery_minutes",
                                lambda x: x.isna().sum())
    )
    .to_string()
)

print("\n===== 7. DUPLICATE ANALYSIS =====")

print("Rows before removing exact duplicates:", len(orders))

deduplicated = orders.drop_duplicates()

print("Rows after removing exact duplicates:", len(deduplicated))
print("Rows removed:", len(orders) - len(deduplicated))

print("\n===== 8. AGE INVESTIGATION =====")

print("Original missing ages:", customers["age"].isna().sum())
print("Invalid ages:", (
    customers["age"].notna()
    & ~customers["age"].between(18, 100)
).sum())

print("\nFINAL INVESTIGATION COMPLETED")