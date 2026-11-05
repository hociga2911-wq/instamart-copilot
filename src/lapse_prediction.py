from pathlib import Path
import pandas as pd

# Project paths
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "clean"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Dates
CUTOFF_DATE = pd.Timestamp("2025-09-01")
LABEL_END_DATE = pd.Timestamp("2025-10-01")

# Load clean data
customers = pd.read_csv(DATA_DIR / "customers_clean.csv")
orders = pd.read_csv(DATA_DIR / "orders_clean.csv")

# Convert order timestamp
orders["order_ts"] = pd.to_datetime(orders["order_ts"])

# Keep only customers with at least one completed order
# before the cutoff date
historical_orders = orders[
    (orders["status"] == "completed") &
    (orders["order_ts"] < CUTOFF_DATE)
].copy()

eligible_customers = historical_orders["customer_id"].unique()

# Customers who completed an order during September
september_orders = orders[
    (orders["status"] == "completed") &
    (orders["order_ts"] >= CUTOFF_DATE) &
    (orders["order_ts"] < LABEL_END_DATE)
]

september_active = set(september_orders["customer_id"].unique())

# Build target labels
cohort = pd.DataFrame({
    "customer_id": eligible_customers
})

cohort["lapsed"] = (
    ~cohort["customer_id"].isin(september_active)
).astype(int)

# Summary
print("\nLAPSE COHORT SUMMARY")
print("--------------------")
print("Eligible customers:", len(cohort))
print("Lapsed customers:", cohort["lapsed"].sum())
print("Active customers:", (cohort["lapsed"] == 0).sum())
print(
    "Lapse percentage:",
    round(cohort["lapsed"].mean() * 100, 2), "%"
)

# Validation
assert cohort["customer_id"].is_unique
assert cohort["lapsed"].isin([0, 1]).all()
assert len(cohort) == 1156
assert cohort["lapsed"].sum() == 443

# Save cohort
cohort.to_csv(
    OUTPUT_DIR / "lapse_cohort.csv",
    index=False
)

print("\nLapse cohort validation passed.")
print("Saved: outputs/lapse_cohort.csv")


# STEP 5: HISTORICAL CUSTOMER FEATURE ENGINEERING

products = pd.read_csv(DATA_DIR / "products_clean.csv")

# Convert dates and numeric columns
customers["signup_date"] = pd.to_datetime(customers["signup_date"])
orders["order_ts"] = pd.to_datetime(orders["order_ts"])

for col in ["order_amount", "discount_pct", "delivery_minutes"]:
    orders[col] = pd.to_numeric(orders[col], errors="coerce")

# Only use orders before September 1, 2025
historical = orders[
    orders["order_ts"] < CUTOFF_DATE
].copy()

# Join product category
historical = historical.merge(
    products[["product_id", "category"]],
    on="product_id",
    how="left"
)

# Completed orders for purchase features
completed = historical[
    historical["status"] == "completed"
].copy()

# Completed-order features
features = completed.groupby("customer_id").agg(
    last_order_ts=("order_ts", "max"),
    first_order_ts=("order_ts", "min"),
    frequency=("order_id", "nunique"),
    monetary=("order_amount", "sum"),
    avg_discount_pct=("discount_pct", "mean"),
    avg_delivery_minutes=("delivery_minutes", "mean")
)

features["recency"] = (
    CUTOFF_DATE - features["last_order_ts"]
).dt.days

features["tenure_days"] = (
    CUTOFF_DATE - features["first_order_ts"]
).dt.days

# Cancellation rate using all final-status orders before cutoff
final_status_orders = historical[
    historical["status"].isin(["completed", "cancelled"])
].copy()

status_counts = final_status_orders.groupby("customer_id").agg(
    total_orders=("order_id", "nunique"),
    cancelled_orders=("status", lambda x: (x == "cancelled").sum())
)

status_counts["cancellation_rate"] = (
    status_counts["cancelled_orders"] /
    status_counts["total_orders"]
)

features = features.join(
    status_counts[["cancellation_rate"]],
    how="left"
)

# Most frequently purchased product category
favourite_category = (
    completed.groupby(["customer_id", "category"])
    .size()
    .reset_index(name="category_count")
    .sort_values(
        ["customer_id", "category_count", "category"],
        ascending=[True, False, True]
    )
    .drop_duplicates("customer_id")
    .set_index("customer_id")["category"]
    .rename("favourite_category")
)

features = features.join(favourite_category)

# Add customer profile information
customer_features = customers[
    ["customer_id", "city", "age", "gender", "signup_date"]
].copy()

customer_features["tenure_days"] = (
    CUTOFF_DATE - customer_features["signup_date"]
).dt.days

features = features.join(
    customer_features.set_index("customer_id")[
        ["city", "age", "gender", "tenure_days"]
    ],
    how="left",
    rsuffix="_customer"
)

# Keep only eligible cohort customers and attach labels
model_data = cohort.merge(
    features.reset_index(),
    on="customer_id",
    how="left"
)

# Use the customer signup-based tenure as the final tenure feature
model_data["tenure_days"] = model_data["tenure_days_customer"]
model_data.drop(columns=["tenure_days_customer"], inplace=True)

# Validate feature data
feature_columns = [
    "recency",
    "frequency",
    "monetary",
    "avg_discount_pct",
    "cancellation_rate",
    "avg_delivery_minutes",
    "favourite_category",
    "city",
    "age",
    "gender",
    "tenure_days"
]

print("\nFEATURE DATASET SUMMARY")
print("-----------------------")
print("Rows:", len(model_data))
print("Columns:", model_data.shape[1])
print("Missing values:")
print(model_data[feature_columns].isna().sum())

# Save feature dataset
model_data.to_csv(
    OUTPUT_DIR / "lapse_features.csv",
    index=False
)

print("\nSaved: outputs/lapse_features.csv")


# STEP 6: TRAIN-TEST SPLIT AND BASELINE

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score

# Separate features and target
X = model_data[feature_columns].copy()
y = model_data["lapsed"].copy()

# Stratified 80/20 split
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    stratify=y,
    random_state=42
)

print("\nTRAIN-TEST SPLIT")
print("----------------")
print("Training rows:", len(X_train))
print("Testing rows:", len(X_test))

print("\nTraining class distribution:")
print(y_train.value_counts().sort_index())

print("\nTesting class distribution:")
print(y_test.value_counts().sort_index())

# Baseline: predict every customer as NOT lapsed
baseline_predictions = [0] * len(y_test)

baseline_accuracy = accuracy_score(
    y_test,
    baseline_predictions
)

baseline_f1 = f1_score(
    y_test,
    baseline_predictions,
    zero_division=0
)

print("\nBASELINE RESULTS")
print("----------------")
print("Accuracy:", round(baseline_accuracy, 4))
print("Lapsed-class F1:", round(baseline_f1, 4))

# Validate split sizes and class balance
assert len(X_train) == 924
assert len(X_test) == 232
assert y_train.sum() + (y_train == 0).sum() == 924
assert y_test.sum() + (y_test == 0).sum() == 232

print("\nTrain-test validation passed.")


# STEP 7: PREPROCESSING PIPELINES

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

numeric_features = [
    "recency",
    "frequency",
    "monetary",
    "avg_discount_pct",
    "cancellation_rate",
    "avg_delivery_minutes",
    "age",
    "tenure_days"
]

categorical_features = [
    "city",
    "gender",
    "favourite_category"
]

# Numerical preprocessing
numeric_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

# Categorical preprocessing
categorical_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(
        drop="first",
        handle_unknown="ignore"
    ))
])

# Combine preprocessing
preprocessor = ColumnTransformer(
    transformers=[
        ("numeric", numeric_transformer, numeric_features),
        ("categorical", categorical_transformer, categorical_features)
    ]
)

# Fit ONLY on training data
X_train_processed = preprocessor.fit_transform(X_train)

# Transform test data without fitting
X_test_processed = preprocessor.transform(X_test)

print("\nPREPROCESSING SUMMARY")
print("---------------------")
print("Training matrix shape:", X_train_processed.shape)
print("Testing matrix shape:", X_test_processed.shape)

# Check scaler learned only from training data
frequency_index = numeric_features.index("frequency")
learned_frequency_mean = (
    preprocessor
    .named_transformers_["numeric"]
    .named_steps["scaler"]
    .mean_[frequency_index]
)

print(
    "Training frequency mean:",
    round(learned_frequency_mean, 4)
)

print(
    "Full cohort frequency mean:",
    round(X["frequency"].mean(), 4)
)

print("\nPreprocessing completed.")


# STEP 8: MODEL TRAINING AND HYPERPARAMETER TUNING

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score
)

# Logistic Regression pipeline
logistic_pipeline = Pipeline(steps=[
    ("preprocessor", ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, numeric_features),
            ("categorical", categorical_transformer, categorical_features)
        ]
    )),
    ("model", LogisticRegression(max_iter=1000))
])

logistic_grid = {
    "model__C": [0.01, 0.1, 1, 10, 100]
}

logistic_search = GridSearchCV(
    logistic_pipeline,
    logistic_grid,
    cv=5,
    scoring="f1",
    n_jobs=-1
)

logistic_search.fit(X_train, y_train)

# Random Forest pipeline
rf_pipeline = Pipeline(steps=[
    ("preprocessor", ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, numeric_features),
            ("categorical", categorical_transformer, categorical_features)
        ]
    )),
    ("model", RandomForestClassifier(
        n_estimators=100,
        random_state=42
    ))
])

rf_grid = {
    "model__max_depth": [3, 5, 8],
    "model__min_samples_leaf": [5, 10, 20]
}

rf_search = GridSearchCV(
    rf_pipeline,
    rf_grid,
    cv=5,
    scoring="f1",
    n_jobs=-1
)

rf_search.fit(X_train, y_train)

# Compare best models on the untouched test set
models = {
    "Logistic Regression": logistic_search.best_estimator_,
    "Random Forest": rf_search.best_estimator_
}

print("\nMODEL TUNING RESULTS")
print("--------------------")

print("\nLogistic Regression")
print("Best parameters:", logistic_search.best_params_)
print("Best CV F1:", round(logistic_search.best_score_, 4))

print("\nRandom Forest")
print("Best parameters:", rf_search.best_params_)
print("Best CV F1:", round(rf_search.best_score_, 4))

print("\nTEST SET RESULTS")
print("----------------")

for name, model in models.items():
    predictions = model.predict(X_test)

    print(f"\n{name}")
    print("Confusion matrix:")
    print(confusion_matrix(y_test, predictions))

    print("Precision:", round(
        precision_score(y_test, predictions, zero_division=0), 4
    ))
    print("Recall:", round(
        recall_score(y_test, predictions, zero_division=0), 4
    ))
    print("F1:", round(
        f1_score(y_test, predictions, zero_division=0), 4
    ))


# STEP 9: MINORITY CLASS OVERSAMPLING

from sklearn.utils import resample

# Separate training classes
train_data = X_train.copy()
train_data["lapsed"] = y_train.values

majority = train_data[train_data["lapsed"] == 0]
minority = train_data[train_data["lapsed"] == 1]

# Duplicate minority rows with replacement
minority_oversampled = resample(
    minority,
    replace=True,
    n_samples=len(majority),
    random_state=42
)

# Combine balanced training data
balanced_train = pd.concat(
    [majority, minority_oversampled],
    ignore_index=True
)

X_train_balanced = balanced_train.drop(columns=["lapsed"])
y_train_balanced = balanced_train["lapsed"]

print("\nOVERSAMPLING SUMMARY")
print("--------------------")
print(y_train_balanced.value_counts().sort_index())

# Refit best Logistic Regression pipeline
balanced_logistic = logistic_search.best_estimator_

balanced_logistic.fit(
    X_train_balanced,
    y_train_balanced
)

# Evaluate on original untouched test data
balanced_predictions = balanced_logistic.predict(X_test)

print("\nOVERSAMPLED LOGISTIC REGRESSION")
print("------------------------------")
print("Confusion matrix:")
print(confusion_matrix(y_test, balanced_predictions))

print("Precision:", round(
    precision_score(
        y_test, balanced_predictions, zero_division=0
    ), 4
))

print("Recall:", round(
    recall_score(
        y_test, balanced_predictions, zero_division=0
    ), 4
))

print("F1:", round(
    f1_score(
        y_test, balanced_predictions, zero_division=0
    ), 4
))


# STEP 10: MODEL INTERPRETATION

# Random Forest feature importance
rf_pipeline = rf_search.best_estimator_
rf_preprocessor = rf_pipeline.named_steps["preprocessor"]
rf_model = rf_pipeline.named_steps["model"]

feature_names = rf_preprocessor.get_feature_names_out()

rf_importance = pd.DataFrame({
    "feature": feature_names,
    "importance": rf_model.feature_importances_
}).sort_values("importance", ascending=False)

print("\nTOP 5 RANDOM FOREST FEATURES")
print("----------------------------")
print(rf_importance.head(5).to_string(index=False))

# Logistic Regression coefficients
lr_pipeline = logistic_search.best_estimator_
lr_preprocessor = lr_pipeline.named_steps["preprocessor"]
lr_model = lr_pipeline.named_steps["model"]

lr_feature_names = lr_preprocessor.get_feature_names_out()

lr_coefficients = pd.DataFrame({
    "feature": lr_feature_names,
    "coefficient": lr_model.coef_[0]
})

lr_coefficients["absolute_coefficient"] = (
    lr_coefficients["coefficient"].abs()
)

lr_coefficients = lr_coefficients.sort_values(
    "absolute_coefficient", ascending=False
)

print("\nTOP 3 POSITIVE LOGISTIC REGRESSION COEFFICIENTS")
print("-----------------------------------------------")
print(
    lr_coefficients[lr_coefficients["coefficient"] > 0]
    .head(3)[["feature", "coefficient"]]
    .to_string(index=False)
)

print("\nTOP 3 NEGATIVE LOGISTIC REGRESSION COEFFICIENTS")
print("------------------------------------------------")
print(
    lr_coefficients[lr_coefficients["coefficient"] < 0]
    .head(3)[["feature", "coefficient"]]
    .to_string(index=False)
)

# STEP 11: SAVE AND VERIFY SELECTED MODEL

import joblib
import numpy as np

model_path = OUTPUT_DIR / "lapse_model.joblib"

# Save original best Logistic Regression pipeline
joblib.dump(logistic_search.best_estimator_, model_path)

print("\nMODEL SAVED")
print("-----------")
print(model_path)

# Reload saved model
loaded_model = joblib.load(model_path)

# Verify predictions are identical
original_predictions = logistic_search.best_estimator_.predict(X_test)
reloaded_predictions = loaded_model.predict(X_test)

predictions_match = np.array_equal(
    original_predictions,
    reloaded_predictions
)

print("\nMODEL RELOAD VALIDATION")
print("-----------------------")
print("Predictions identical:", predictions_match)

assert predictions_match, "Reloaded model predictions do not match!"

print("Model save/load validation passed.")

# STEP 12: PREMIUM CUSTOMER RETENTION LIST

# Load customer segments
segments = pd.read_csv(OUTPUT_DIR / "customer_segments.csv")

# Get test customer IDs using the preserved original row indices
test_customer_ids = model_data.loc[X_test.index, "customer_id"].values

# Predict lapse probabilities using the saved model
loaded_model = joblib.load(OUTPUT_DIR / "lapse_model.joblib")
lapse_probabilities = loaded_model.predict_proba(X_test)[:, 1]

# Actual test labels
actual_labels = y_test.values

# Build test prediction dataset
retention_predictions = pd.DataFrame({
    "customer_id": test_customer_ids,
    "lapse_probability": lapse_probabilities,
    "actually_lapsed": actual_labels
})

# Keep premium customers only
premium_test = segments[
    segments["is_premium"].astype(bool)
][["customer_id"]]

retention_list = retention_predictions.merge(
    premium_test,
    on="customer_id",
    how="inner"
)

# Rank by predicted lapse probability
retention_list = retention_list.sort_values(
    "lapse_probability",
    ascending=False
)

# Save top 10 premium customers
retention_list = retention_list.head(10)

retention_list["lapse_probability"] = (
    retention_list["lapse_probability"].round(4)
)

retention_list.to_csv(
    OUTPUT_DIR / "retention_list.csv",
    index=False
)

print("\nPREMIUM CUSTOMER RETENTION LIST")
print("--------------------------------")
print("Premium customers in test set:", len(premium_test.merge(
    retention_predictions[["customer_id"]],
    on="customer_id",
    how="inner"
)))
print("Customers in retention list:", len(retention_list))
print(
    "Actually lapsed among top 10:",
    int(retention_list["actually_lapsed"].sum())
)
print("\nTop 10 customers:")
print(retention_list.to_string(index=False))

print("\nSaved: outputs/retention_list.csv")