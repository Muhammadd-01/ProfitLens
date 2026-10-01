"""Customer Segmentation and K-Means Clustering Service.

Unsupervised machine learning module that clusters customer behavioral vectors (RFM, AOV, Lifespan),
finds optimal k via Silhouette and Elbow methods, generates 2D PCA projections, and assigns automated
business personas with marketing recommendations.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.dataset import Dataset
from app.schemas.ml import (
    SegmentProfile,
    ElbowPoint,
    PCAPoint,
    SegmentationTrainResponse,
)
from app.services.cleaning_service import load_dataset_as_dataframe
from app.services.feature_service import compute_customer_rfm_features
from app.services.mapping_service import get_dataset_mapping_suggestions


def preprocess_customer_features(df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
    """Log-transforms heavy-tailed columns and scales features with StandardScaler."""
    feature_cols = ["recency_days", "frequency", "monetary_total", "avg_order_value", "customer_lifespan_days"]
    
    # Ensure all feature columns exist
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0.0

    X_raw = df[feature_cols].copy().fillna(0.0)

    # Log-transform heavy-tailed monetary and count variables: log(1 + x)
    log_cols = ["frequency", "monetary_total", "avg_order_value", "customer_lifespan_days"]
    for col in log_cols:
        X_raw[col] = np.log1p(np.maximum(0.0, X_raw[col].values))

    # Standardize to zero mean, unit variance
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    return X_scaled, feature_cols


def evaluate_optimal_k(X_scaled: np.ndarray, max_k: int = 6) -> Tuple[List[ElbowPoint], int]:
    """Evaluates cluster cohesion (Inertia) and separation (Silhouette) for k in [2, max_k]."""
    n_samples = len(X_scaled)
    upper_k = min(max_k, max(2, n_samples - 1))
    
    elbow_points: List[ElbowPoint] = []
    best_k = 4
    best_silhouette = -1.0

    for k in range(2, upper_k + 1):
        kmeans = KMeans(n_clusters=k, init="k-means++", random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        
        inertia = float(kmeans.inertia_)
        sil = float(silhouette_score(X_scaled, labels)) if n_samples > k else 0.0

        elbow_points.append(ElbowPoint(k=k, inertia=round(inertia, 2), silhouette=round(sil, 3)))

        # Choose best k based on silhouette score
        if sil > best_silhouette:
            best_silhouette = sil
            best_k = k

    # If silhouette preferred k=2, but k=3 or 4 has reasonable silhouette (> 0.25), prefer k >= 3 for business utility
    if best_k == 2 and len(elbow_points) >= 2:
        k3_candidates = [p for p in elbow_points if p.k in [3, 4] and p.silhouette >= 0.25]
        if k3_candidates:
            best_k = k3_candidates[0].k

    return elbow_points, best_k


def generate_segment_personas(
    df: pd.DataFrame,
    cluster_col: str = "cluster",
) -> List[SegmentProfile]:
    """Inspects cluster centroids and automatically assigns business personas and strategies."""
    total_cust = len(df)
    clusters = sorted(df[cluster_col].unique())
    k = len(clusters)

    # Compute centroid stats per cluster
    stats = []
    for c in clusters:
        cdf = df[df[cluster_col] == c]
        stats.append({
            "cluster_id": int(c),
            "count": len(cdf),
            "pct": round((len(cdf) / total_cust) * 100.0, 1),
            "r_mean": float(cdf["recency_days"].mean()),
            "f_mean": float(cdf["frequency"].mean()),
            "m_mean": float(cdf["monetary_total"].mean()),
            "aov_mean": float(cdf["avg_order_value"].mean()),
        })

    # Sort clusters to identify roles:
    # Champions: highest monetary & frequency
    # At Risk: high monetary but high recency
    # New/Promising: low frequency, low recency
    # Inactive: low monetary, high recency
    sorted_by_m = sorted(stats, key=lambda s: s["m_mean"], reverse=True)
    champ_id = sorted_by_m[0]["cluster_id"]

    sorted_by_r = sorted(stats, key=lambda s: s["r_mean"], reverse=True)
    lost_id = sorted_by_r[0]["cluster_id"]

    profiles: List[SegmentProfile] = []
    for s in stats:
        cid = s["cluster_id"]
        
        if cid == champ_id:
            label = "Champions & VIPs"
            description = "High-value, highly active customers with highest lifetime spend and frequency."
            color = "#10b981"  # Emerald
            strategy = "Reward loyalty with exclusive early access, dedicated account support, and referral bonuses."
        elif cid == lost_id and cid != champ_id:
            label = "At Risk & Inactive"
            description = "Customers with long elapsed periods since last purchase who are at severe risk of churn."
            color = "#ef4444"  # Red
            strategy = "Deploy targeted re-activation email sequences with compelling limited-time incentives."
        elif s["f_mean"] >= 2.0:
            label = "Loyal Regulars"
            description = "Consistent repeat buyers with solid order frequency and steady revenue generation."
            color = "#3b82f6"  # Blue
            strategy = "Cross-sell related categories and incentivize subscription or bundle options."
        else:
            label = "Promising & Newcomers"
            description = "Recent buyers with low transaction frequency who have potential to become loyalists."
            color = "#8b5cf6"  # Purple
            strategy = "Provide onboarding tutorials, welcome discounts, and prompt for second purchase within 14 days."

        profiles.append(
            SegmentProfile(
                cluster_id=cid,
                label=label,
                description=description,
                customer_count=s["count"],
                percentage=s["pct"],
                avg_recency=round(s["r_mean"], 1),
                avg_frequency=round(s["f_mean"], 1),
                avg_monetary=round(s["m_mean"], 2),
                avg_order_value=round(s["aov_mean"], 2),
                color=color,
                strategy_recommendation=strategy,
            )
        )

    return profiles


async def run_customer_segmentation(
    dataset_id: str,
    organization_id: str,
    k_clusters: Optional[int] = None,
    db: Optional[AsyncIOMotorDatabase] = None,
) -> SegmentationTrainResponse:
    """Executes customer segmentation pipeline on dataset in MongoDB."""
    if db is None:
        raise ValueError("Database session required")

    doc = await db.datasets.find_one({
        "$or": [{"id": str(dataset_id)}, {"_id": str(dataset_id)}],
        "organization_id": str(organization_id),
    })
    if not doc:
        raise ValueError(f"Dataset {dataset_id} not found")
    dataset = Dataset.from_doc(doc)
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} not found")

    base_dir = os.path.dirname(dataset.file_path)
    cust_features_file = os.path.join(base_dir, f"{dataset.id}_customer_features.csv")

    # If customer features table does not exist, compute it now
    if not os.path.exists(cust_features_file):
        col_meta = dataset.column_metadata or {}
        cleaned_file = col_meta.get("cleaned_file_path")
        file_to_load = cleaned_file if cleaned_file and os.path.exists(cleaned_file) else dataset.file_path
        raw_df = load_dataset_as_dataframe(file_to_load, dataset.file_type)

        mappings = dataset.column_mappings or {}
        if not mappings:
            mapping_resp = await get_dataset_mapping_suggestions(dataset_id, organization_id, db)
            mappings = {m.canonical_field: m.mapped_column for m in mapping_resp.mappings if m.mapped_column}

        cust_col = mappings.get("customer_id")
        date_col = mappings.get("order_date")
        rev_col = mappings.get("revenue")
        ord_col = mappings.get("order_id")
        cat_col = mappings.get("category")

        if not cust_col or not date_col or not rev_col:
            raise ValueError("Segmentation requires mapped customer_id, order_date, and revenue columns")

        cust_df, _ = compute_customer_rfm_features(
            df=raw_df,
            customer_id_col=cust_col,
            date_col=date_col,
            revenue_col=rev_col,
            order_id_col=ord_col,
            category_col=cat_col,
        )
        cust_df.to_csv(cust_features_file, index=False)
    else:
        cust_df = pd.read_csv(cust_features_file)

    if len(cust_df) < 5:
        raise ValueError(f"Customer segmentation requires at least 5 customers with purchase history. Found: {len(cust_df)}")

    # 1. Preprocess & Scale
    X_scaled, _ = preprocess_customer_features(cust_df)

    # 2. Optimal k evaluation
    elbow_curve, best_k = evaluate_optimal_k(X_scaled, max_k=6)
    optimal_k = k_clusters if (k_clusters is not None and 2 <= k_clusters <= 6) else best_k

    # 3. Fit K-Means
    kmeans = KMeans(n_clusters=optimal_k, init="k-means++", random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    cust_df["cluster"] = labels

    sil_score = float(silhouette_score(X_scaled, labels)) if len(cust_df) > optimal_k else 0.0

    # 4. Dimensionality Reduction with PCA
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X_scaled)
    cust_df["pca_x"] = np.round(coords[:, 0], 3)
    cust_df["pca_y"] = np.round(coords[:, 1], 3)
    var_explained = round(float(pca.explained_variance_ratio_.sum()) * 100.0, 1)

    # 5. Persona Profiles
    profiles = generate_segment_personas(cust_df, cluster_col="cluster")
    cluster_to_label = {p.cluster_id: p.label for p in profiles}
    cust_df["segment_label"] = cust_df["cluster"].map(cluster_to_label)

    # Save segmented customer dataset
    seg_file = os.path.join(base_dir, f"{dataset.id}_customer_segments.csv")
    cust_df.to_csv(seg_file, index=False)

    # 6. Sample Points for 2D Scatter Visualization (max 300 points)
    sample_size = min(300, len(cust_df))
    scatter_df = cust_df.sample(n=sample_size, random_state=42) if len(cust_df) > sample_size else cust_df

    pca_points: List[PCAPoint] = []
    for _, row in scatter_df.iterrows():
        pca_points.append(
            PCAPoint(
                customer_id=str(row["customer_id"]),
                x=float(row["pca_x"]),
                y=float(row["pca_y"]),
                cluster_id=int(row["cluster"]),
                label=str(row["segment_label"]),
                monetary=round(float(row["monetary_total"]), 2),
                frequency=int(row["frequency"]),
                recency=int(row["recency_days"]),
            )
        )

    trained_at = datetime.utcnow().isoformat()

    # Update database metadata in MongoDB
    col_meta = dataset.column_metadata or {}
    col_meta["segmentation_results"] = {
        "dataset_id": str(dataset.id),
        "optimal_k": optimal_k,
        "silhouette_score": round(sil_score, 3),
        "total_customers": len(cust_df),
        "pca_variance_explained": var_explained,
        "segments": [p.model_dump() for p in profiles],
        "elbow_curve": [e.model_dump() for e in elbow_curve],
        "trained_at": trained_at,
    }

    await db.datasets.update_one(
        {"$or": [{"id": dataset.id}, {"_id": dataset.id}]},
        {"$set": {
            "column_metadata": col_meta,
            "updated_at": datetime.utcnow(),
        }}
    )

    return SegmentationTrainResponse(
        dataset_id=str(dataset.id),
        optimal_k=optimal_k,
        silhouette_score=round(sil_score, 3),
        total_customers=len(cust_df),
        pca_variance_explained=var_explained,
        segments=profiles,
        elbow_curve=elbow_curve,
        pca_scatter=pca_points,
        trained_at=trained_at,
    )
