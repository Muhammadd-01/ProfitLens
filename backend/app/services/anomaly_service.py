"""Transaction Anomaly Detection Service.

Unsupervised machine learning module combining Isolation Forest with Median Absolute
Deviation (Modified Z-Score). Scans transaction ledgers for monetary spikes, quantity
irregularities, velocity bursts, and category-relative discrepancies with automated
root-cause explanations and operator review workflows.
"""

from __future__ import annotations

import os
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.dataset import Dataset
from app.models.analysis import Anomaly, AnalysisRun
from app.schemas.ml import (
    AnomalyItem,
    AnomalySeverityDistribution,
    AnomalyOverviewResponse,
)
from app.services.cleaning_service import load_dataset_as_dataframe
from app.services.mapping_service import get_dataset_mapping_suggestions


def compute_anomaly_features(
    df: pd.DataFrame,
    order_id_col: str,
    date_col: str,
    revenue_col: str,
    cust_col: Optional[str] = None,
    qty_col: Optional[str] = None,
    cat_col: Optional[str] = None,
    disc_col: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """Extracts multivariate features for isolation forest and statistical outlier checks."""
    data = df.copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce", utc=True)
    data[revenue_col] = pd.to_numeric(data[revenue_col], errors="coerce").fillna(0.0)
    data = data.dropna(subset=[order_id_col, date_col, revenue_col])

    # Category-relative ratio
    if cat_col and cat_col in data.columns:
        cat_medians = data.groupby(cat_col)[revenue_col].transform("median")
        data["category_median"] = cat_medians.fillna(data[revenue_col].median())
        data["cat_ratio"] = (data[revenue_col] / np.maximum(1.0, data["category_median"])).round(2)
    else:
        global_med = float(data[revenue_col].median()) if len(data) > 0 else 1.0
        data["category_median"] = global_med
        data["cat_ratio"] = (data[revenue_col] / max(1.0, global_med)).round(2)

    # Quantity feature
    if qty_col and qty_col in data.columns:
        data["quantity_feature"] = pd.to_numeric(data[qty_col], errors="coerce").fillna(1.0)
    else:
        data["quantity_feature"] = 1.0

    # Discount feature
    if disc_col and disc_col in data.columns:
        data["discount_feature"] = pd.to_numeric(data[disc_col], errors="coerce").fillna(0.0)
    else:
        data["discount_feature"] = 0.0

    # Hour of transaction
    data["order_hour"] = data[date_col].dt.hour.fillna(12.0)

    # Customer velocity (order count in same 24h window)
    if cust_col and cust_col in data.columns:
        data = data.sort_values([cust_col, date_col])
        # Rolling count of orders per customer in 24h window
        data["order_velocity_24h"] = 1.0
        try:
            # Approximate by grouping by customer and day
            cust_day_counts = data.groupby([cust_col, data[date_col].dt.date])[order_id_col].transform("count")
            data["order_velocity_24h"] = cust_day_counts.astype(float)
        except Exception:
            data["order_velocity_24h"] = 1.0
    else:
        data["order_velocity_24h"] = 1.0

    feature_cols = [
        revenue_col,
        "cat_ratio",
        "quantity_feature",
        "discount_feature",
        "order_velocity_24h",
    ]

    X = data[feature_cols].copy().fillna(0.0)
    return X, data, feature_cols


def run_isolation_and_mad_scoring(
    X: pd.DataFrame,
    data: pd.DataFrame,
    revenue_col: str,
    contamination: float = 0.02,
) -> pd.DataFrame:
    """Ensembles Isolation Forest path length and Modified Z-Score into unified anomaly probability."""
    res_df = data.copy()
    n = len(X)
    
    # 1. Isolation Forest
    iso = IsolationForest(
        n_estimators=100,
        contamination=min(0.15, max(0.005, contamination)),
        random_state=42,
        n_jobs=1,
    )
    iso.fit(X)
    raw_scores = iso.decision_function(X)  # Lower is more abnormal
    iso_preds = iso.predict(X)  # -1 is outlier, 1 is inlier

    # Invert and normalize to [0, 1]
    min_s, max_s = float(np.min(raw_scores)), float(np.max(raw_scores))
    rng = max(1e-6, max_s - min_s)
    iso_prob = 1.0 - ((raw_scores - min_s) / rng)

    # 2. Modified Z-Score (Median Absolute Deviation) on revenue
    rev_vals = res_df[revenue_col].values
    med_rev = float(np.median(rev_vals))
    mad = float(np.median(np.abs(rev_vals - med_rev)))
    mad_denom = max(1.0, mad)
    mod_z = (0.6745 * np.abs(rev_vals - med_rev)) / mad_denom
    # Map Z-scores into [0, 1] via sigmoid-like transformation
    mad_prob = 1.0 / (1.0 + np.exp(-0.8 * (mod_z - 3.5)))

    # Combined Ensemble Score (60% Isolation Forest + 40% MAD)
    combined_score = 0.6 * iso_prob + 0.4 * mad_prob
    res_df["anomaly_score"] = np.round(combined_score, 3)
    res_df["is_iso_outlier"] = (iso_preds == -1)
    res_df["mod_z_score"] = np.round(mod_z, 2)

    return res_df


def synthesize_anomaly_explanations(
    row: pd.Series,
    revenue_col: str,
) -> Tuple[str, str, Dict[str, Any]]:
    """Builds human-readable root-cause explanations and determines severity tier."""
    score = float(row["anomaly_score"])
    amount = float(row[revenue_col])
    cat_ratio = float(row.get("cat_ratio", 1.0))
    cat_med = float(row.get("category_median", amount))
    qty = float(row.get("quantity_feature", 1.0))
    disc = float(row.get("discount_feature", 0.0))
    vel = float(row.get("order_velocity_24h", 1.0))
    z_sc = float(row.get("mod_z_score", 0.0))

    reasons = []

    # Amount & Category ratio
    if cat_ratio >= 5.0 or z_sc >= 6.0:
        reasons.append(f"Extreme revenue spike: ${amount:,.2f} is {cat_ratio:.1f}x the category median (${cat_med:,.2f}).")
    elif cat_ratio >= 2.5 or z_sc >= 3.5:
        reasons.append(f"Unusually high transaction value: ${amount:,.2f} exceeds cohort expectation (${cat_med:,.2f}).")

    # Quantity
    if qty >= 15:
        reasons.append(f"Bulk purchase irregularity: {int(qty)} units ordered (standard is 1-3).")

    # Discount
    if disc >= 0.50:
        reasons.append(f"Abnormally steep discount: {int(disc * 100)}% markdown applied.")
    elif disc < 0.0:
        reasons.append(f"Negative discount anomaly ({disc}) detected.")

    # Velocity
    if vel >= 4:
        reasons.append(f"High-frequency burst: {int(vel)} orders placed by same account within 24 hours.")

    if not reasons:
        reasons.append(f"Multivariate outlier: combination of amount (${amount:,.2f}) and order attributes deviates from baseline.")

    primary_reason = reasons[0]

    # Severity Tier Determination
    if score >= 0.82 or cat_ratio >= 8.0 or z_sc >= 8.0 or (disc >= 0.70 and amount > 500):
        severity = "critical"
    elif score >= 0.68 or cat_ratio >= 4.0 or z_sc >= 4.5 or vel >= 5:
        severity = "high"
    elif score >= 0.52 or cat_ratio >= 2.5:
        severity = "medium"
    else:
        severity = "low"

    details = {
        "amount": amount,
        "category_median": cat_med,
        "category_ratio": cat_ratio,
        "modified_z_score": z_sc,
        "quantity": qty,
        "discount": disc,
        "velocity_24h": vel,
        "contributing_factors": reasons,
    }

    return severity, primary_reason, details


async def run_transaction_anomaly_detection(
    dataset_id: str,
    organization_id: str,
    contamination: Optional[float] = 0.02,
    sensitivity: Optional[str] = "balanced",
    db: Optional[AsyncIOMotorDatabase] = None,
) -> AnomalyOverviewResponse:
    """Executes transaction anomaly detection pipeline, records findings in DB, and returns dashboard summary."""
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

    # Load cleaned or original dataset
    col_meta = dataset.column_metadata or {}
    cleaned_file = col_meta.get("cleaned_file_path")
    file_to_load = cleaned_file if cleaned_file and os.path.exists(cleaned_file) else dataset.file_path
    raw_df = load_dataset_as_dataframe(file_to_load, dataset.file_type)

    # Resolve column mappings
    mappings = dataset.column_mappings or {}
    if not mappings:
        mapping_resp = await get_dataset_mapping_suggestions(dataset_id, organization_id, db)
        mappings = {m.canonical_field: m.mapped_column for m in mapping_resp.mappings if m.mapped_column}

    ord_col = mappings.get("order_id")
    date_col = mappings.get("order_date")
    rev_col = mappings.get("revenue")
    cust_col = mappings.get("customer_id")
    qty_col = mappings.get("quantity")
    cat_col = mappings.get("category")
    disc_col = mappings.get("discount")

    if not ord_col or not date_col or not rev_col:
        raise ValueError("Anomaly detection requires mapped order_id, order_date, and revenue columns")

    # Contamination threshold adjustments based on sensitivity
    contam = contamination or 0.02
    if sensitivity == "aggressive":
        contam = min(0.08, contam * 1.8)
    elif sensitivity == "conservative":
        contam = max(0.005, contam * 0.6)

    # 1. Compute features
    X, data_enriched, feature_cols = compute_anomaly_features(
        df=raw_df,
        order_id_col=ord_col,
        date_col=date_col,
        revenue_col=rev_col,
        cust_col=cust_col,
        qty_col=qty_col,
        cat_col=cat_col,
        disc_col=disc_col,
    )

    if len(X) < 10:
        raise ValueError(f"Anomaly detection requires at least 10 orders. Found {len(X)}.")

    # 2. Fit Isolation Forest & Modified Z-score
    scored_df = run_isolation_and_mad_scoring(
        X=X,
        data=data_enriched,
        revenue_col=rev_col,
        contamination=contam,
    )

    # 3. Filter candidate anomalies: top anomalous cohort or score >= 0.45
    score_cutoff = np.percentile(scored_df["anomaly_score"], (1.0 - contam) * 100.0)
    cutoff = min(0.65, max(0.40, score_cutoff))
    anomalies_df = scored_df[
        (scored_df["anomaly_score"] >= cutoff) | (scored_df["is_iso_outlier"] == True)
    ].copy()

    detected_at = datetime.utcnow().isoformat()
    anomaly_items: List[AnomalyItem] = []
    crit_c, high_c, med_c, low_c = 0, 0, 0, 0
    total_flagged_rev = 0.0

    # Sort descending by anomaly score
    anomalies_df = anomalies_df.sort_values("anomaly_score", reverse=True if hasattr(anomalies_df, "reverse") else False, ascending=False)

    for idx, row in anomalies_df.iterrows():
        severity, reason, details = synthesize_anomaly_explanations(row, rev_col)
        amt = round(float(row[rev_col]), 2)
        total_flagged_rev += amt

        if severity == "critical":
            crit_c += 1
        elif severity == "high":
            high_c += 1
        elif severity == "medium":
            med_c += 1
        else:
            low_c += 1

        ord_id = str(row[ord_col])
        cust_id = str(row[cust_col]) if cust_col and cust_col in row and pd.notna(row[cust_col]) else None
        o_date = pd.to_datetime(row[date_col]).strftime("%Y-%m-%d %H:%M")

        item = AnomalyItem(
            id=str(uuid.uuid4()),
            order_id=ord_id,
            customer_id=cust_id,
            order_date=o_date,
            amount=amt,
            anomaly_score=float(row["anomaly_score"]),
            severity=severity,
            reason=reason,
            details=details,
            is_reviewed=False,
            review_status="pending",
            detected_at=detected_at,
        )
        anomaly_items.append(item)

    distribution = AnomalySeverityDistribution(
        critical_count=crit_c,
        high_count=high_c,
        medium_count=med_c,
        low_count=low_c,
        total_anomalies=len(anomaly_items),
        total_flagged_revenue=round(total_flagged_rev, 2),
        reviewed_count=0,
    )

    # 4. Save results to CSV
    anomaly_csv = os.path.join(base_dir, f"{dataset.id}_anomalies.csv")
    export_records = []
    for a in anomaly_items:
        rec = a.model_dump()
        rec["details"] = json.dumps(rec.get("details", {}))
        export_records.append(rec)

    if export_records:
        export_df = pd.DataFrame(export_records)
        export_df.to_csv(anomaly_csv, index=False)

    # 5. Persist into dataset metadata
    col_meta["anomaly_results"] = {
        "dataset_id": str(dataset.id),
        "total_orders_scanned": len(scored_df),
        "distribution": distribution.model_dump(),
        "total_anomalies": len(anomaly_items),
        "detected_at": detected_at,
        "anomaly_file_path": anomaly_csv,
    }

    await db.datasets.update_one(
        {"$or": [{"id": dataset.id}, {"_id": dataset.id}]},
        {"$set": {
            "column_metadata": col_meta,
            "updated_at": datetime.utcnow(),
        }}
    )

    return AnomalyOverviewResponse(
        dataset_id=str(dataset.id),
        total_orders_scanned=len(scored_df),
        distribution=distribution,
        anomalies=anomaly_items,
        detected_at=detected_at,
    )


async def get_or_run_anomalies(
    dataset_id: str,
    organization_id: str,
    db: AsyncIOMotorDatabase,
) -> AnomalyOverviewResponse:
    """Retrieve saved anomaly detection results from CSV and metadata, or trigger initial run in MongoDB."""
    doc = await db.datasets.find_one({
        "$or": [{"id": str(dataset_id)}, {"_id": str(dataset_id)}],
        "organization_id": str(organization_id),
    })
    if not doc:
        raise ValueError(f"Dataset {dataset_id} not found")
    dataset = Dataset.from_doc(doc)
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} not found")

    col_meta = dataset.column_metadata or {}
    saved_meta = col_meta.get("anomaly_results")
    if saved_meta:
        anomaly_csv = saved_meta.get("anomaly_file_path")
        if anomaly_csv and os.path.exists(anomaly_csv):
            try:
                df = pd.read_csv(anomaly_csv)
                anomalies: List[AnomalyItem] = []
                for _, row in df.iterrows():
                    details_raw = row.get("details", "{}")
                    try:
                        details_val = json.loads(details_raw) if isinstance(details_raw, str) else {}
                    except Exception:
                        details_val = {}

                    anomalies.append(
                        AnomalyItem(
                            id=str(row["id"]),
                            order_id=str(row["order_id"]),
                            customer_id=str(row["customer_id"]) if pd.notna(row.get("customer_id")) else None,
                            order_date=str(row["order_date"]),
                            amount=float(row["amount"]),
                            anomaly_score=float(row["anomaly_score"]),
                            severity=str(row["severity"]),
                            reason=str(row["reason"]),
                            details=details_val,
                            is_reviewed=bool(row.get("is_reviewed", False)),
                            review_status=str(row.get("review_status", "pending")),
                            detected_at=str(row.get("detected_at", saved_meta.get("detected_at", ""))),
                        )
                    )
                dist_data = saved_meta.get("distribution", {})
                distribution = AnomalySeverityDistribution(
                    critical_count=dist_data.get("critical_count", 0),
                    high_count=dist_data.get("high_count", 0),
                    medium_count=dist_data.get("medium_count", 0),
                    low_count=dist_data.get("low_count", 0),
                    total_anomalies=dist_data.get("total_anomalies", len(anomalies)),
                    total_flagged_revenue=dist_data.get("total_flagged_revenue", 0.0),
                    reviewed_count=dist_data.get("reviewed_count", sum(1 for a in anomalies if a.is_reviewed)),
                )
                return AnomalyOverviewResponse(
                    dataset_id=str(dataset.id),
                    total_orders_scanned=saved_meta.get("total_orders_scanned", len(anomalies)),
                    distribution=distribution,
                    anomalies=anomalies,
                    detected_at=saved_meta.get("detected_at", datetime.utcnow().isoformat()),
                )
            except Exception:
                pass

    return await run_transaction_anomaly_detection(
        dataset_id=dataset_id,
        organization_id=organization_id,
        contamination=0.02,
        sensitivity="balanced",
        db=db,
    )


async def review_anomaly_record(
    dataset_id: str,
    organization_id: str,
    anomaly_id: str,
    review_status: str,
    notes: Optional[str] = None,
    db: Optional[AsyncIOMotorDatabase] = None,
) -> AnomalyItem:
    """Updates the operator review status for a specific detected anomaly record in MongoDB."""
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

    col_meta = dataset.column_metadata or {}
    saved_meta = col_meta.get("anomaly_results", {})
    anomaly_csv = saved_meta.get("anomaly_file_path")
    if not anomaly_csv or not os.path.exists(anomaly_csv):
        raise ValueError("No anomaly records found for this dataset. Please run detection first.")

    df = pd.read_csv(anomaly_csv)
    idx_matches = df.index[df["id"].astype(str) == str(anomaly_id)].tolist()
    if not idx_matches:
        idx_matches = df.index[df["order_id"].astype(str) == str(anomaly_id)].tolist()
        if not idx_matches:
            raise ValueError(f"Anomaly {anomaly_id} not found")

    target_idx = idx_matches[0]
    df.at[target_idx, "is_reviewed"] = True
    df.at[target_idx, "review_status"] = review_status

    row = df.iloc[target_idx]
    details_raw = row.get("details", "{}")
    try:
        details_val = json.loads(details_raw) if isinstance(details_raw, str) else {}
    except Exception:
        details_val = {}

    if notes:
        details_val["reviewer_notes"] = notes
    df.at[target_idx, "details"] = json.dumps(details_val)
    df.to_csv(anomaly_csv, index=False)

    reviewed_count = int(df["is_reviewed"].sum())
    if "distribution" in saved_meta:
        saved_meta["distribution"]["reviewed_count"] = reviewed_count
        col_meta["anomaly_results"] = saved_meta

        await db.datasets.update_one(
            {"$or": [{"id": dataset.id}, {"_id": dataset.id}]},
            {"$set": {
                "column_metadata": col_meta,
                "updated_at": datetime.utcnow(),
            }}
        )

    return AnomalyItem(
        id=str(row["id"]),
        order_id=str(row["order_id"]),
        customer_id=str(row["customer_id"]) if pd.notna(row.get("customer_id")) else None,
        order_date=str(row["order_date"]),
        amount=float(row["amount"]),
        anomaly_score=float(row["anomaly_score"]),
        severity=str(row["severity"]),
        reason=str(row["reason"]),
        details=details_val,
        is_reviewed=True,
        review_status=review_status,
        detected_at=str(row.get("detected_at", datetime.utcnow().isoformat())),
    )

