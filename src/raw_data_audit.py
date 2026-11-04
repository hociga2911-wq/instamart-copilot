from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

FILES = [
    "customers.csv",
    "orders.csv",
    "products.csv",
]

for filename in FILES:
    path = RAW / filename
    df = pd.read_csv(path)

    audit = pd.DataFrame({
        "column": df.columns,
        "dtype": [str(df[col].dtype) for col in df.columns],
        "missing_count": [int(df[col].isna().sum()) for col in df.columns],
        "missing_pct": [
            round(float(df[col].isna().mean() * 100), 2)
            for col in df.columns
        ],
    })

    print(f"\n{'=' * 65}")
    print(f"FILE: {filename}")
    print(f"SHAPE: {df.shape[0]} rows x {df.shape[1]} columns")
    print(audit.to_string(index=False))

    if filename == "customers.csv":
        age = pd.to_numeric(df["age"], errors="coerce")
        print("\nCustomer reference checks:")
        print("Blank age:", int(df["age"].isna().sum()))
        print("Age outside 10-100:", int((~age.between(10, 100)).sum()))
        print("Distinct raw city spellings:", int(df["city"].nunique()))
        print(
            "Distinct nonblank raw gender spellings:",
            int(df.loc[df["gender"].notna() & df["gender"].astype(str).str.strip().ne(""), "gender"].nunique())
        )
        print("Blank gender:", int(df["gender"].isna().sum()))

    elif filename == "orders.csv":
        amount = pd.to_numeric(df["order_amount"], errors="coerce")
        print("\nOrder reference checks:")
        print("Exact duplicate rows:", int(df.duplicated().sum()))
        print("Pending rows:", int(df["status"].astype(str).str.lower().eq("pending").sum()))
        print("Distinct order IDs:", int(df["order_id"].nunique()))
        print("Order amounts not convertible to numeric:", int(amount.isna().sum()))
        delivery = pd.to_numeric(df["delivery_minutes"], errors="coerce")
        print("Negative delivery times:", int(delivery.lt(0).sum()))
        print("Blank delivery times:", int(df["delivery_minutes"].isna().sum()))

    audit.to_csv(OUT / f"{path.stem}_audit.csv", index=False)

print(f"\nAudit column summaries saved to: {OUT}")
