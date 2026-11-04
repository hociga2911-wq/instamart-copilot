# Instamart Customer Intelligence & Support Copilot

## Part A: Data Cleaning, SQL, and Pandas Analysis

### 1. Environment setup

Create and activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

### 2. Raw data audit

```powershell
python src/raw_data_audit.py
```

Audit summaries are saved under `outputs/`.

### 3. Clean the data

```powershell
python src/clean_data.py
```

Cleaned CSV files and a cleaning report are saved under `data/clean/`.

### 4. Create the SQLite database

```powershell
python src/create_database.py
```

Database location: `data/instamart.db`.

Tables: `customers`, `products`, and `orders`.

### 5. Run the SQL analysis

```powershell
python src/run_sql.py
```

The seven SQL queries are in `sql/queries.sql`.

### 6. Run the pandas analysis

```powershell
python src/pandas_analysis.py
```

### 7. Validate the results

```powershell
python src/validate_cleaning.py
```

Expected final message:

`ALL CHECKPOINTS PASSED`

## Reproducibility notes

- Run commands from the project root.
- Keep the supplied `generate_data.py` and `mock_llm.py` unchanged.
- Run `generate_data.py` only when a fresh raw dataset is intended.
- Do not commit `.env` files or the virtual environment.
- Monetary values are reported in INR.
