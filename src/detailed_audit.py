
from pathlib import Path
import pandas as pd

RAW = Path("data/raw")

customers = pd.read_csv(RAW / "customers.csv")
orders = pd.read_csv(RAW / "orders.csv")

print("\n========== CUSTOMER INVESTIGATION ==========")

print("\nAge summary:")
print(customers["age"].describe())

print("\nImpossible ages:")
print(customers.loc[
    (customers["age"] < 0) | (customers["age"] > 100),
    ["customer_id", "age"]
].to_string(index=False))

print("\nRaw city spellings:")
cities = sorted(customers["city"].dropna().unique())
for city in cities:
    print(repr(city))

print("\nGender values:")
print(customers["gender"].value_counts(dropna=False))

print("\n========== ORDER INVESTIGATION ==========")

print("\nOrder status counts:")
print(orders["status"].value_counts(dropna=False))

print("\nDistinct order IDs:")
print(orders["order_id"].nunique())

print("\nExact duplicate rows:")
print(orders.duplicated().sum())

amount = pd.to_numeric(orders["order_amount"], errors="coerce")

print("\nInvalid or missing order amounts:")
print(amount.isna().sum())

print("\nNonnumeric nonblank amounts:")
print(
    (orders["order_amount"].notna() & amount.isna()).sum()
)

print("\nNegative delivery times:")
print((orders["delivery_minutes"] < 0).sum())

print("\nMissing delivery times:")
print(orders["delivery_minutes"].isna().sum())

print("\nPending order rows:")
print(
    orders["status"].astype(str).str.lower().str.strip()
    .eq("pending").sum()
)

print("\n========== AUDIT COMPLETE ==========")