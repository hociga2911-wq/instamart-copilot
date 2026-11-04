

from pathlib import Path
import json
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

RAW = Path("data/raw")
CLEAN = Path("data/clean")
CLEAN.mkdir(parents=True, exist_ok=True)

report = {}


def record(name, value):
    """Record a count in the cleaning report and print it."""
    report[name] = int(value)
    print(f"{name}: {value}")


def save_csv(df, *filenames):
    """Save a DataFrame under one or more filenames."""
    for filename in filenames:
        df.to_csv(CLEAN / filename, index=False)


def require(condition, message):
    """Stop cleaning if an important data requirement fails."""
    if not condition:
        raise ValueError(message)


# ============================================================
# 1. CUSTOMER CLEANING
# ============================================================

print("\n========== CUSTOMER CLEANING ==========")

customers = pd.read_csv(RAW / "customers.csv")
record("customers_before", len(customers))

# Remove exact duplicate customer records.
before = len(customers)
customers = customers.drop_duplicates().copy()
record("customer_exact_duplicates_removed", before - len(customers))

# Standardize city spelling.
customers["city"] = (
    customers["city"]
    .astype("string")
    .str.strip()
    .str.title()
)

# Normalize gender spellings.
gender = (
    customers["gender"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
)

gender_map = {
    "m": "male",
    "male": "male",
    "man": "male",
    "f": "female",
    "female": "female",
    "woman": "female",
}

customers["gender"] = gender.map(gender_map).fillna("unknown")

record(
    "unknown_genders_after_normalization",
    customers["gender"].eq("unknown").sum(),
)

# Parse age and invalidate values outside 10–100.
customers["age"] = pd.to_numeric(
    customers["age"], errors="coerce"
)

invalid_age = ~customers["age"].between(10, 100)
record("invalid_ages_converted_to_missing", invalid_age.sum())

customers.loc[invalid_age, "age"] = float("nan")

record(
    "missing_ages_before_imputation",
    customers["age"].isna().sum(),
)

# Impute missing ages with each city's median using groupby + transform.
city_median_age = customers.groupby("city")["age"].transform("median")
customers["age"] = customers["age"].fillna(city_median_age)

# Defensive fallback if an entire city has no valid ages.
overall_median_age = customers["age"].median()
customers["age"] = customers["age"].fillna(overall_median_age)

require(
    customers["age"].notna().all(),
    "Customer ages remain missing after median imputation.",
)

customers["age"] = customers["age"].round().astype(int)

# Convert signup_date to datetime.
customers["signup_date"] = pd.to_datetime(
    customers["signup_date"], errors="coerce"
)

record("missing_ages_after_imputation", customers["age"].isna().sum())
record("customers_after", len(customers))

print("\nCustomer counts by city:")
print(customers["city"].value_counts(dropna=False).to_string())

print("\nCustomer counts by gender:")
print(customers["gender"].value_counts(dropna=False).to_string())

save_csv(customers, "customers.csv", "customers_clean.csv")


# ============================================================
# 2. PRODUCT CLEANING
# ============================================================

print("\n========== PRODUCT CLEANING ==========")

products = pd.read_csv(RAW / "products.csv")
record("products_before", len(products))

before = len(products)
products = products.drop_duplicates().copy()
record("product_exact_duplicates_removed", before - len(products))

products["product_name"] = (
    products["product_name"].astype("string").str.strip()
)
products["category"] = (
    products["category"].astype("string").str.strip().str.title()
)
products["price_inr"] = pd.to_numeric(
    products["price_inr"], errors="coerce"
)

require(
    products["product_id"].is_unique,
    "Product IDs must be unique to calculate order amounts safely.",
)
require(
    products["price_inr"].notna().all(),
    "A product has a missing or invalid price.",
)

record("products_after", len(products))

save_csv(products, "products.csv", "products_clean.csv")


# ============================================================
# 3. ORDER CLEANING
# ============================================================

print("\n========== ORDER CLEANING ==========")

orders = pd.read_csv(RAW / "orders.csv")
record("orders_before", len(orders))

# Audit figures from the raw orders table.
record("raw_exact_duplicate_rows", orders.duplicated().sum())
record(
    "raw_pending_rows",
    orders["status"].astype("string").str.strip().str.lower().eq("pending").sum(),
)
record("raw_distinct_order_ids", orders["order_id"].nunique())

raw_amount_numeric = pd.to_numeric(
    orders["order_amount"], errors="coerce"
)

# Count non-numeric, non-blank values separately from blank values.
raw_amount_text = orders["order_amount"].astype("string").str.strip()
raw_non_numeric = (
    raw_amount_numeric.isna()
    & raw_amount_text.notna()
    & raw_amount_text.ne("")
)
record("raw_non_numeric_order_amounts", raw_non_numeric.sum())

raw_delivery_numeric = pd.to_numeric(
    orders["delivery_minutes"], errors="coerce"
)
record(
    "raw_negative_delivery_times",
    (raw_delivery_numeric < 0).sum(),
)
raw_delivery_text = orders["delivery_minutes"].astype("string").str.strip()
record(
    "raw_blank_delivery_times",
    (
        raw_delivery_text.isna()
        | raw_delivery_text.eq("")
    ).sum(),
)

# Rule 1: Parse order timestamps first.
orders["order_ts"] = pd.to_datetime(
    orders["order_ts"], errors="coerce"
)

require(
    orders["order_ts"].notna().all(),
    "Some order timestamps could not be parsed.",
)

# Rule 2: Remove exact duplicate rows.
before_exact_dedup = len(orders)
orders = orders.drop_duplicates().copy()

exact_duplicates_removed = before_exact_dedup - len(orders)
record("exact_duplicate_rows_removed", exact_duplicates_removed)

# Rule 3: Keep only the latest timestamp per order_id.
# A pending snapshot must not be retained when a later final state exists.
rows_before_latest_selection = len(orders)

orders = (
    orders.sort_values("order_ts", kind="stable")
    .drop_duplicates(subset=["order_id"], keep="last")
    .copy()
)

record(
    "older_order_state_rows_removed",
    rows_before_latest_selection - len(orders),
)

orders["status"] = (
    orders["status"]
    .astype("string")
    .str.strip()
    .str.lower()
)

record("orders_after_latest_record_selection", len(orders))

require(
    orders["order_id"].is_unique,
    "Order IDs are not unique after latest-record selection.",
)
require(
    not orders["status"].eq("pending").any(),
    "Pending orders remain after selecting the latest record.",
)

# Convert numeric columns.
orders["quantity"] = pd.to_numeric(
    orders["quantity"], errors="coerce"
)
orders["discount_pct"] = pd.to_numeric(
    orders["discount_pct"], errors="coerce"
)
orders["order_amount"] = pd.to_numeric(
    orders["order_amount"], errors="coerce"
)
orders["delivery_minutes"] = pd.to_numeric(
    orders["delivery_minutes"], errors="coerce"
)

require(
    orders[["quantity", "discount_pct"]].notna().all().all(),
    "Quantity or discount is missing or invalid.",
)

# Join product price/category for amount calculation and delivery imputation.
orders = orders.merge(
    products[["product_id", "price_inr", "category"]],
    on="product_id",
    how="left",
    validate="many_to_one",
)

require(
    orders["price_inr"].notna().all(),
    "At least one order has no matching product price.",
)
require(
    orders["category"].notna().all(),
    "At least one order has no matching product category.",
)

# Rule 4: Fill missing/unparseable amounts using the prescribed formula.
missing_amount = orders["order_amount"].isna()
record("missing_order_amounts_before_imputation", missing_amount.sum())

calculated_amount = (
    orders["price_inr"]
    * orders["quantity"]
    * (1 - orders["discount_pct"] / 100)
).round(2)

orders.loc[missing_amount, "order_amount"] = (
    calculated_amount.loc[missing_amount]
)

require(
    orders["order_amount"].notna().all(),
    "Some order amounts remain missing after imputation.",
)

# Rule 5: Negative delivery times become missing.
negative_delivery = orders["delivery_minutes"] < 0
record("negative_delivery_times_fixed", negative_delivery.sum())

orders.loc[negative_delivery, "delivery_minutes"] = float("nan")

# Cancelled orders must have missing delivery times.
cancelled = orders["status"].eq("cancelled")
orders.loc[cancelled, "delivery_minutes"] = float("nan")

# Impute missing completed delivery times using the completed-order
# median for the same product category.
completed = orders["status"].eq("completed")

completed_category_medians = (
    orders.loc[completed]
    .groupby("category")["delivery_minutes"]
    .transform("median")
)

missing_completed_delivery = (
    completed & orders["delivery_minutes"].isna()
)
record(
    "missing_completed_delivery_times_before_imputation",
    missing_completed_delivery.sum(),
)

orders.loc[completed, "delivery_minutes"] = (
    orders.loc[completed, "delivery_minutes"]
    .fillna(completed_category_medians)
)

require(
    orders.loc[completed, "delivery_minutes"].notna().all(),
    "Completed orders still have missing delivery times.",
)

# Remove temporary columns used for lookups.
orders = orders.drop(columns=["price_inr", "category"])

# Ensure timestamps are saved in the specified text format.
orders["order_ts"] = pd.to_datetime(
    orders["order_ts"]
).dt.strftime("%Y-%m-%d %H:%M:%S")

# Record final checks.
record("orders_after", len(orders))
record("completed_orders_after", orders["status"].eq("completed").sum())
record("cancelled_orders_after", orders["status"].eq("cancelled").sum())
record("pending_orders_after", orders["status"].eq("pending").sum())
record("missing_order_amounts_after", orders["order_amount"].isna().sum())

record(
    "missing_completed_delivery_times_after",
    orders.loc[
        orders["status"].eq("completed"), "delivery_minutes"
    ].isna().sum(),
)
record(
    "missing_cancelled_delivery_times_after",
    orders.loc[
        orders["status"].eq("cancelled"), "delivery_minutes"
    ].isna().sum(),
)

completed_revenue = orders.loc[
    orders["status"].eq("completed"), "order_amount"
].sum()

print(f"Completed revenue: INR {completed_revenue:.2f}")

save_csv(orders, "orders.csv", "orders_clean.csv")


# ============================================================
# 4. TICKET CLEANING
# ============================================================

print("\n========== TICKET CLEANING ==========")

# keep_default_na=False preserves empty ticket fields as empty strings.
tickets = pd.read_csv(
    RAW / "tickets.csv",
    keep_default_na=False,
)

record("tickets_before", len(tickets))

before = len(tickets)
tickets = tickets.drop_duplicates().copy()
record("ticket_exact_duplicates_removed", before - len(tickets))

tickets["text"] = tickets["text"].astype(str).str.strip()
tickets["true_category"] = (
    tickets["true_category"].astype(str).str.strip().str.lower()
)

record("blank_ticket_texts_after_cleaning", tickets["text"].eq("").sum())
record("tickets_after", len(tickets))

save_csv(tickets, "tickets_clean.csv")


# ============================================================
# 5. POLICY EVALUATION CLEANING
# ============================================================

print("\n========== POLICY EVALUATION CLEANING ==========")

policy = pd.read_csv(RAW / "policy_eval.csv")
record("policy_eval_before", len(policy))

before = len(policy)
policy = policy.drop_duplicates().copy()
record("policy_exact_duplicates_removed", before - len(policy))

for column in policy.columns:
    policy[column] = (
        policy[column].astype("string").str.strip()
    )

record("policy_eval_after", len(policy))
save_csv(policy, "policy_eval_clean.csv")


# ============================================================
# 6. SAVE CLEANING REPORT
# ============================================================

report_path = CLEAN / "cleaning_report.json"

with open(report_path, "w", encoding="utf-8") as file:
    json.dump(report, file, indent=4)

print("\n========== CLEANING COMPLETED ==========")
print(json.dumps(report, indent=4))
print(f"\nCleaning report saved to: {report_path.resolve()}")
print(f"Cleaned files saved in: {CLEAN.resolve()}")
