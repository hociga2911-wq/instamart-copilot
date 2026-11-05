# Instamart Customer Intelligence & Support Copilot
## Part A: Data Cleaning, SQL, and Pandas Analysis

This project implements a reproducible data-cleaning and analysis pipeline for Instamart customer, product, and order data. It includes raw-data auditing, data cleaning, SQLite database creation, seven SQL analyses, pandas-based analysis, and automated validation.

All monetary values are reported in Indian Rupees (INR).

## 1. Project Structure

```text
instamart-copilot/
├── data/
│   ├── raw/                 # Original generated datasets
│   ├── clean/               # Cleaned CSV files and cleaning report
│   ├── policies/            # Supplied policy text files
│   └── instamart.db         # SQLite database
├── outputs/
│   ├── customers_audit.csv
│   ├── orders_audit.csv
│   ├── products_audit.csv
│   ├── city_summary.csv
│   ├── correlation_matrix.csv
│   ├── order_amount_distribution.csv
│   ├── revenue_pivot.csv
│   └── sql_results.txt
├── sql/
│   ├── queries.sql          # Seven SQL analysis queries
│   └── analysis_queries.sql
├── src/
│   ├── raw_data_audit.py
│   ├── clean_data.py
│   ├── create_database.py
│   ├── cleaning_investigation.py
│   ├── detailed_audit.py
│   └── part_a.py
│   ├── run_sql.py
│   ├── pandas_analysis.py
│   └── validate_cleaning.py
├── generate_data.py         # Supplied data generator
├── mock_llm.py              # Supplied mock LLM
├── requirements.txt
├── .gitignore
└── README.md
```

## 2. Environment Setup

### Prerequisites

- Python installed and available on the command line
- Git
- Windows PowerShell or a compatible terminal

Run all commands from the project root directory.

### Create and activate the virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The `requirements.txt` file records the project's Python package dependencies.

## 3. Raw Data Audit

Run the audit before cleaning the data:

```powershell
python src/raw_data_audit.py
```

The audit examines dataset dimensions, column data types, missing-value counts, and missing-value percentages for the raw customer, order, and product datasets.

### Raw dataset summary

| Dataset | Rows | Columns |
|---|---:|---:|
| Customers | 1,200 | 5 |
| Orders | 13,084 | 9 |
| Products | 40 | 4 |

### Important audit findings

**Customers**

- 61 missing age values.
- 30 missing gender values.
- 24 distinct raw city spellings.
- 10 distinct nonblank raw gender spellings.
- 6 nonmissing ages outside the valid 10–100 range.

**Orders**

- 119 exact duplicate rows.
- 656 pending-state snapshots.
- 12,309 distinct order IDs.
- 120 order-amount entries that cannot be converted to numeric values, including missing entries.
- 106 negative delivery-time values.
- 2,541 blank delivery-time values.

**Products**

- 40 product records.

Column-level audit reports are saved in `outputs/customers_audit.csv`, `outputs/orders_audit.csv`, and `outputs/products_audit.csv`.

## 4. Data Cleaning

Run the cleaning pipeline:

```powershell
python src/clean_data.py
```

Cleaned CSV files and a cleaning report are written to `data/clean/`.

### 4.1 Customer cleaning

The customer-cleaning process:

1. Checks the original customer data and duplicate records.
2. Trims whitespace and standardizes city names using title case.
3. Maps gender values to `male`, `female`, or `unknown`.
4. Converts nonmissing ages outside 10–100 to missing values.
5. Fills missing ages using the median age for the corresponding city.
6. Converts `signup_date` to datetime.
7. Verifies the cleaned customer records and key fields.

The cleaned customer dataset contains 1,200 records with unique customer IDs, six standardized cities, three normalized gender categories, and no missing ages.

### 4.2 Product cleaning

The product dataset is checked for duplicate product IDs and basic data integrity. The cleaned dataset contains 40 product records.

### 4.3 Order cleaning

Order cleaning follows this sequence:

1. Parse `order_ts` as datetime.
2. Remove 119 exact duplicate rows.
3. Retain the latest timestamped record for each `order_id`, resolving earlier order-state snapshots.
4. Convert `order_amount` to numeric.
5. Impute missing or invalid order amounts using:

   `price_inr × quantity × (1 − discount_pct / 100)`

   The imputed amount is rounded to two decimal places.
6. Replace negative delivery times with missing values.
7. Fill missing delivery times for completed orders using the median delivery time for the corresponding product category among completed orders.
8. Leave delivery times missing for cancelled orders.
9. Verify order uniqueness, statuses, amounts, and delivery-time rules.

### Final order counts

| Measure | Result |
|---|---:|
| Raw order rows | 13,084 |
| Exact duplicate rows removed | 119 |
| Older order-state records removed | 656 |
| Final unique orders | 12,309 |
| Completed orders | 11,110 |
| Cancelled orders | 1,199 |
| Pending orders remaining | 0 |
| Missing order amounts after cleaning | 0 |
| Completed orders missing delivery time | 0 |
| Cancelled orders with missing delivery time | 1,199 |
| Completed-order revenue | INR 2,998,668.80 |

The final dataset contains one record per order ID. No pending orders remain after selecting the latest record for each order.

## 5. SQLite Database

Create the database from the cleaned CSV files:

```powershell
python src/create_database.py
```

The database is stored at:

`data/instamart.db`

It contains the following tables:

| Table | Description |
|---|---|
| `customers` | Cleaned customer information |
| `products` | Cleaned product catalogue |
| `orders` | Cleaned order records |

The database creation script checks the expected table counts and verifies that the final orders do not contain pending statuses.

## 6. SQL Analysis

Run the seven SQL analyses:

```powershell
python src/run_sql.py
```

The queries are stored in `sql/queries.sql`. They are executed from Python against `data/instamart.db` using `pandas.read_sql_query`.

The analyses cover:

1. **High-value customer orders:** Completed orders above INR 500, grouped by customer, with a total-spend threshold above INR 8,000.
2. **Revenue by city and product category:** Joins orders, customers, and products to aggregate completed-order revenue.
3. **Above-average-priced products:** Identifies products priced above the catalogue average.
4. **Customers without completed orders:** Uses a left join to identify customers with no completed order.
5. **Above-average customer spend:** Uses a common table expression (CTE) to identify customers whose completed-order spend exceeds the average among customers with completed orders.
6. **Customer spend rankings:** Uses `RANK()`, `DENSE_RANK()`, and `ROW_NUMBER()` to rank customers by completed-order spend within each city.
7. **Daily revenue and cumulative revenue:** Aggregates completed-order revenue by day and calculates a running total using a window function.

SQL execution results are saved in `outputs/sql_results.txt`.

### Key SQL results

- Total completed-order revenue: **INR 2,998,668.80**
- Revenue aggregation by city and product category: 30 city-category combinations.
- Products priced above the catalogue average: 11.
- Customers with no completed order: 25.
- Customers above the average completed-order spend: 550.
- Daily revenue records: 183.
- Final cumulative revenue: INR 2,998,668.80.

## 7. Pandas Analysis

Run the pandas analyses:

```powershell
python src/pandas_analysis.py
```

The script produces the following outputs.

### Revenue pivot table

`outputs/revenue_pivot.csv`

Uses `pandas.pivot_table` to summarize completed-order revenue by city and product category, including row and column grand totals.

### City-level summary

`outputs/city_summary.csv`

Uses `groupby` with named aggregation to calculate total revenue, mean order amount, and order count for each city.

Example results:

| City | Revenue (INR) | Mean order amount (INR) | Order count |
|---|---:|---:|---:|
| Bengaluru | 523,643.40 | 276.47 | 1,894 |
| Chennai | 463,629.15 | 272.72 | 1,700 |
| Delhi | 502,829.80 | 243.62 | 2,064 |
| Hyderabad | 528,589.90 | 284.95 | 1,855 |
| Mumbai | 479,058.50 | 297.00 | 1,613 |
| Pune | 500,918.05 | 252.48 | 1,984 |

### Order-amount distribution

`outputs/order_amount_distribution.csv`

Summarizes completed-order amount statistics, including the mean, median, quartiles, skewness, interquartile range, and IQR-based outlier thresholds.

Key results:

- Mean order amount: INR 269.91.
- Median order amount: INR 135.00.
- First quartile (Q1): INR 64.80.
- Third quartile (Q3): INR 297.00.
- Skewness: approximately 4.61.
- Upper IQR outlier fence: INR 645.30.
- Orders above the upper fence: 897.

The positive skewness indicates that a relatively small number of high-value orders extend the upper tail of the distribution.

### Correlation analysis

`outputs/correlation_matrix.csv`

Calculates correlations among `order_amount`, `discount_pct`, `quantity`, and `delivery_minutes`.

The strongest absolute pairwise correlation is between order amount and discount percentage, at approximately −0.095. This is a weak negative correlation and does not establish a causal relationship.

## 8. Automated Validation

Run the validation script after cleaning and database creation:

```powershell
python src/validate_cleaning.py
```

The script checks customer, product, and order counts; unique IDs; normalized fields; order statuses; missing values; delivery-time rules; database tables; and completed-order revenue.

A successful run should end with:

```text
21 CHECKPOINTS PASSED
ALL CHECKPOINTS PASSED
```

The final line, `ALL CHECKPOINTS PASSED`, confirms that the implemented validation checks succeeded.

## 9. Reproducing the Pipeline

From the project root, with the virtual environment activated, run:

```powershell
python -m pip install -r requirements.txt
python src/raw_data_audit.py
python src/clean_data.py
python src/create_database.py
python src/run_sql.py
python src/pandas_analysis.py
python src/validate_cleaning.py
```

This sequence audits the raw data, creates cleaned datasets, builds the SQLite database, executes the SQL analyses, generates pandas outputs, and validates the results.

**Important:** The supplied `generate_data.py` and `mock_llm.py` files must remain unchanged. Do not run `generate_data.py` during normal reproduction unless you intentionally want to generate a fresh raw dataset.

## 10. Version Control and Project Hygiene

- Run commands from the project root.
- Keep the virtual environment in `.venv/`.
- Do not commit `.env` files, virtual-environment files, or Python cache files.
- Keep `requirements.txt` updated when dependencies change.
- Use Git commits to record meaningful project milestones.
- Report monetary values in INR.

## 11. Summary

Part A provides a reproducible workflow for raw-data auditing, customer and order cleaning, SQLite database creation, SQL querying, pandas-based analysis, and automated data-quality validation. The resulting datasets and analysis outputs can serve as the data foundation for subsequent customer-intelligence and support-copilot development.
