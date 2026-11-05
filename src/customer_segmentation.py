
from pathlib import Path

import pandas as pd


# Project paths
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "clean"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Load cleaned Part A data
customers = pd.read_csv(DATA_DIR / "customers.csv")
orders = pd.read_csv(DATA_DIR / "orders.csv")

# Snapshot moment
SNAPSHOT = pd.Timestamp("2025-10-01 00:00:00")

# Parse date and numeric columns
orders["order_ts"] = pd.to_datetime(orders["order_ts"], errors="coerce")
orders["order_amount"] = pd.to_numeric(
    orders["order_amount"], errors="coerce"
)

# Keep completed orders only
completed = orders.loc[
    orders["status"].str.lower().eq("completed")
].copy()

# Calculate RFM for each customer
rfm = (
    completed.groupby("customer_id")
    .agg(
        last_order_ts=("order_ts", "max"),
        frequency=("order_id", "nunique"),
        monetary=("order_amount", "sum"),
    )
    .reset_index()
)

# Recency = whole days between snapshot and last completed order
rfm["recency"] = (
    SNAPSHOT - rfm["last_order_ts"]
).dt.days

# Keep the required RFM columns
rfm = rfm[
    ["customer_id", "recency", "frequency", "monetary"]
].copy()

# Sort for convenient inspection
rfm = rfm.sort_values("customer_id").reset_index(drop=True)

# Save intermediate RFM table
rfm.to_csv(OUTPUT_DIR / "rfm_table.csv", index=False)

# Print reference-check statistics
print("\nRFM TABLE SUMMARY")
print("-----------------")
print("Customers:", len(rfm))

print("\nRecency:")
print(rfm["recency"].agg(["median", "min", "max"]))

print("\nFrequency:")
print(rfm["frequency"].agg(["mean", "max"]))

print("\nMonetary:")
print(rfm["monetary"].agg(["mean", "max"]))

# Basic validation
assert len(rfm) == 1175, "Unexpected RFM customer count"
assert rfm["customer_id"].is_unique, "Duplicate customer IDs in RFM"
assert rfm[["recency", "frequency", "monetary"]].notna().all().all()

print("\nRFM validation passed.")
print("Saved: outputs/rfm_table.csv")


# ============================================================
# STEP 2: K-MEANS CLUSTERING
# ============================================================

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# Select the three RFM features
rfm_features = ["recency", "frequency", "monetary"]
X = rfm[rfm_features].copy()

# Standardise RFM features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Test K values from 2 to 8
clustering_results = []

for k in range(2, 9):
    kmeans = KMeans(
        n_clusters=k,
        n_init=10,
        random_state=42
    )

    labels = kmeans.fit_predict(X_scaled)

    inertia = kmeans.inertia_
    silhouette = silhouette_score(X_scaled, labels)

    clustering_results.append({
        "K": k,
        "Inertia": inertia,
        "Silhouette": silhouette
    })

# Display results
clustering_table = pd.DataFrame(clustering_results)

print("\nK-MEANS EVALUATION")
print("------------------")
print(clustering_table.to_string(
    index=False,
    formatters={
        "Inertia": "{:.1f}".format,
        "Silhouette": "{:.3f}".format
    }
))

# Save results
clustering_table.to_csv(
    OUTPUT_DIR / "kmeans_evaluation.csv",
    index=False
)

print("\nSaved: outputs/kmeans_evaluation.csv")

# STEP 3: FINAL CUSTOMER SEGMENTATION

from sklearn.decomposition import PCA

# Fit final K-Means model with K=4
final_kmeans = KMeans(
    n_clusters=4,
    n_init=10,
    random_state=42
)

rfm["segment_id"] = final_kmeans.fit_predict(X_scaled)

# Profile each cluster
segment_profile = (
    rfm.groupby("segment_id")
    .agg(
        customers=("customer_id", "count"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean")
    )
    .round(2)
)

print("\nSEGMENT PROFILES")
print("----------------")
print(segment_profile)

# PCA for 2D visualization analysis
pca = PCA(n_components=2)
pca_result = pca.fit_transform(X_scaled)

print("\nPCA EXPLAINED VARIANCE")
print("----------------------")
print("PC1:", round(pca.explained_variance_ratio_[0], 3))
print("PC2:", round(pca.explained_variance_ratio_[1], 3))
print(
    "Total:",
    round(pca.explained_variance_ratio_.sum(), 3)
)

# Save PCA coordinates
rfm["pca_1"] = pca_result[:, 0]
rfm["pca_2"] = pca_result[:, 1]

# Assign business-friendly segment names
segment_names = {
    0: "Occasional Customers",
    1: "Premium Customers",
    2: "Loyal Customers",
    3: "At-Risk Customers"
}

rfm["segment_name"] = rfm["segment_id"].map(segment_names)

# Identify Premium customers
rfm["is_premium"] = (
    rfm["segment_name"] == "Premium Customers"
)

# Save final customer segmentation
rfm[
    [
        "customer_id",
        "recency",
        "frequency",
        "monetary",
        "segment_id",
        "segment_name",
        "is_premium"
    ]
].to_csv(
    "outputs/customer_segments.csv",
    index=False
)

print("\nFINAL SEGMENT COUNTS")
print("--------------------")
print(rfm["segment_name"].value_counts())

print("\nPremium customers:", rfm["is_premium"].sum())
print("Saved: outputs/customer_segments.csv")

# Save segment profile
segment_profile.to_csv(
    "outputs/segment_profile.csv"
)

print("\nSaved: outputs/segment_profile.csv")