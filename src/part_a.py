
from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")

def audit_csv(file_path):
    print("\n" + "=" * 65)
    print(f"FILE: {file_path.name}")
    print("=" * 65)

    df = pd.read_csv(file_path)

    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    print("\nColumn names:")
    print(df.columns.tolist())

    print("\nData types:")
    print(df.dtypes.to_string())

    print("\nMissing values:")
    print(df.isna().sum().to_string())

    print("\nExact duplicate rows:")
    print(df.duplicated().sum())

    print("\nFirst 3 records:")
    print(df.head(3).to_string(index=False))


def main():
    print("INSTAMART DATA AUDIT")
    print("=" * 65)

    for file_path in sorted(RAW_DIR.glob("*.csv")):
        audit_csv(file_path)

    print("\nAUDIT COMPLETED")


if __name__ == "__main__":
    main()