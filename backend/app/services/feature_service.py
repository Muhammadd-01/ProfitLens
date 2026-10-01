"""Feature Engineering Service for ProfitLens.

Transforms irregular transactional business records into model-ready features:
1. Customer-Level Features: RFM (Recency, Frequency, Monetary), AOV, Lifespan, Inter-arrival times.
2. Time-Series Features: Daily regularized aggregation, autoregressive lags, rolling statistics,
   and cyclical seasonal encodings (sin/cos).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.dataset import Dataset
from app.schemas.dataset import (
    FeatureCatalogItem,
    CustomerFeatureSummary,
    TimeSeriesFeatureSummary,
    FeatureEngineeringResponse,
)
from app.services.cleaning_service import load_dataset_as_dataframe
from app.services.mapping_service import get_dataset_mapping_suggestions


def compute_customer_rfm_features(
    df: pd.DataFrame,
    customer_id_col: str,
    date_col: str,
    revenue_col: str,
    order_id_col: Optional[str] = None,
    category_col: Optional[str] = None,
) -> Tuple[pd.DataFrame, List[FeatureCatalogItem]]:
    """Engineers RFM, customer lifetime, and behavioral features from transaction log."""
    # Ensure correct data types
    work_df = df.copy()
    work_df = work_df.dropna(subset=[customer_id_col, date_col, revenue_col])
    work_df[date_col] = pd.to_datetime(work_df[date_col], errors="coerce", utc=True)
    work_df = work_df.dropna(subset=[date_col])
    work_df[revenue_col] = pd.to_numeric(work_df[revenue_col], errors="coerce").fillna(0.0)

    # Reference date is max transaction date + 1 day
    ref_date = work_df[date_col].max() + timedelta(days=1)

    # Group by customer
    grouped = work_df.groupby(customer_id_col)

    # Base aggregations
    agg_dict = {
        date_col: ["max", "min"],
        revenue_col: ["sum", "mean", "min", "max"],
    }
    if order_id_col and order_id_col in work_df.columns:
        agg_dict[order_id_col] = "nunique"

    cust_agg = grouped.agg(agg_dict)
    
    # Flatten column MultiIndex
    cust_df = pd.DataFrame(index=cust_agg.index)
    cust_df["last_purchase_date"] = cust_agg[(date_col, "max")]
    cust_df["first_purchase_date"] = cust_agg[(date_col, "min")]
    cust_df["monetary_total"] = cust_agg[(revenue_col, "sum")].round(2)
    cust_df["avg_order_value"] = cust_agg[(revenue_col, "mean")].round(2)
    cust_df["min_order_value"] = cust_agg[(revenue_col, "min")].round(2)
    cust_df["max_order_value"] = cust_agg[(revenue_col, "max")].round(2)

    if order_id_col and order_id_col in work_df.columns:
        cust_df["frequency"] = cust_agg[(order_id_col, "nunique")]
    else:
        cust_df["frequency"] = grouped.size()

    # Derived temporal features
    cust_df["recency_days"] = (ref_date - cust_df["last_purchase_date"]).dt.days
    cust_df["customer_lifespan_days"] = (
        cust_df["last_purchase_date"] - cust_df["first_purchase_date"]
    ).dt.days

    # Purchase inter-arrival time (mean days between orders)
    # For customers with >= 2 orders: lifespan / (frequency - 1)
    cust_df["purchase_interval_mean"] = 0.0
    multi_order_mask = cust_df["frequency"] > 1
    cust_df.loc[multi_order_mask, "purchase_interval_mean"] = (
        cust_df.loc[multi_order_mask, "customer_lifespan_days"]
        / (cust_df.loc[multi_order_mask, "frequency"] - 1)
    ).round(1)

    # Preferred category (mode)
    if category_col and category_col in work_df.columns:
        preferred = (
            work_df.groupby([customer_id_col, category_col])
            .size()
            .reset_index(name="count")
            .sort_values([customer_id_col, "count"], ascending=[True, False])
            .drop_duplicates(subset=[customer_id_col])
            .set_index(customer_id_col)[category_col]
        )
        cust_df["preferred_category"] = preferred.reindex(cust_df.index).fillna("Unknown")

    # Quantile-based RFM Scoring (1 to 5)
    # Recency: lower is better (inverted quantiles)
    try:
        r_labels = [5, 4, 3, 2, 1]
        cust_df["r_score"] = pd.qcut(cust_df["recency_days"].rank(method="first"), q=5, labels=r_labels).astype(int)
    except Exception:
        cust_df["r_score"] = 3

    # Frequency: higher is better
    try:
        f_labels = [1, 2, 3, 4, 5]
        cust_df["f_score"] = pd.qcut(cust_df["frequency"].rank(method="first"), q=5, labels=f_labels).astype(int)
    except Exception:
        cust_df["f_score"] = 3

    # Monetary: higher is better
    try:
        m_labels = [1, 2, 3, 4, 5]
        cust_df["m_score"] = pd.qcut(cust_df["monetary_total"].rank(method="first"), q=5, labels=m_labels).astype(int)
    except Exception:
        cust_df["m_score"] = 3

    cust_df["rfm_composite"] = (
        cust_df["r_score"].astype(str)
        + cust_df["f_score"].astype(str)
        + cust_df["m_score"].astype(str)
    )

    cust_df = cust_df.reset_index()

    # Catalog Items
    catalog = [
        FeatureCatalogItem(
            name="recency_days",
            feature_group="Customer RFM",
            data_type="int",
            description="Days since most recent transaction relative to observation period end",
            downstream_model="Customer Churn & Retention",
            mean_value=float(cust_df["recency_days"].mean()),
            min_value=float(cust_df["recency_days"].min()),
            max_value=float(cust_df["recency_days"].max()),
        ),
        FeatureCatalogItem(
            name="frequency",
            feature_group="Customer RFM",
            data_type="int",
            description="Total number of distinct purchase transactions completed by the customer",
            downstream_model="Customer Segmentation & CLV",
            mean_value=float(cust_df["frequency"].mean()),
            min_value=float(cust_df["frequency"].min()),
            max_value=float(cust_df["frequency"].max()),
        ),
        FeatureCatalogItem(
            name="monetary_total",
            feature_group="Customer RFM",
            data_type="float",
            description="Lifetime gross revenue generated by the customer",
            downstream_model="Customer Lifetime Value (CLV)",
            mean_value=float(cust_df["monetary_total"].mean()),
            min_value=float(cust_df["monetary_total"].min()),
            max_value=float(cust_df["monetary_total"].max()),
        ),
        FeatureCatalogItem(
            name="avg_order_value",
            feature_group="Customer Behavior",
            data_type="float",
            description="Average monetary spend per transaction (Monetary / Frequency)",
            downstream_model="Pricing & Basket Analysis",
            mean_value=float(cust_df["avg_order_value"].mean()),
            min_value=float(cust_df["avg_order_value"].min()),
            max_value=float(cust_df["avg_order_value"].max()),
        ),
        FeatureCatalogItem(
            name="purchase_interval_mean",
            feature_group="Customer Behavior",
            data_type="float",
            description="Average elapsed days between consecutive orders for returning customers",
            downstream_model="Predictive Churn Detection",
            mean_value=float(
                cust_df[cust_df["frequency"] > 1]["purchase_interval_mean"].mean()
                if (cust_df["frequency"] > 1).any()
                else 0.0
            ),
            min_value=0.0,
            max_value=float(cust_df["purchase_interval_mean"].max()),
        ),
        FeatureCatalogItem(
            name="customer_lifespan_days",
            feature_group="Customer Behavior",
            data_type="int",
            description="Days elapsed between first transaction and most recent transaction",
            downstream_model="Cohort Retention & Decay",
            mean_value=float(cust_df["customer_lifespan_days"].mean()),
            min_value=float(cust_df["customer_lifespan_days"].min()),
            max_value=float(cust_df["customer_lifespan_days"].max()),
        ),
    ]

    return cust_df, catalog


def compute_timeseries_features(
    df: pd.DataFrame,
    date_col: str,
    revenue_col: str,
    order_id_col: Optional[str] = None,
) -> Tuple[pd.DataFrame, List[FeatureCatalogItem]]:
    """Engineers regularized daily time series, lag features, rolling windows, and cyclical encodings."""
    work_df = df.copy()
    work_df[date_col] = pd.to_datetime(work_df[date_col], errors="coerce", utc=True)
    work_df = work_df.dropna(subset=[date_col])
    work_df[revenue_col] = pd.to_numeric(work_df[revenue_col], errors="coerce").fillna(0.0)

    # Extract date part
    work_df["day_date"] = work_df[date_col].dt.date

    # Daily aggregation
    if order_id_col and order_id_col in work_df.columns:
        daily = work_df.groupby("day_date").agg(
            daily_revenue=(revenue_col, "sum"),
            daily_orders=(order_id_col, "nunique"),
        )
    else:
        daily = work_df.groupby("day_date").agg(
            daily_revenue=(revenue_col, "sum"),
            daily_orders=(revenue_col, "count"),
        )

    # Reindex to full daily range to prevent irregular gaps
    min_date = daily.index.min()
    max_date = daily.index.max()
    full_idx = pd.date_range(start=min_date, end=max_date, freq="D").date
    daily = daily.reindex(full_idx, fill_value=0.0)
    daily.index.name = "date"
    daily = daily.reset_index()

    # Derived daily KPIs
    daily["daily_revenue"] = daily["daily_revenue"].round(2)
    daily["avg_daily_order_value"] = (
        daily["daily_revenue"] / daily["daily_orders"].replace(0, 1)
    ).round(2)

    # Autoregressive Lags
    daily["revenue_lag_1"] = daily["daily_revenue"].shift(1).fillna(daily["daily_revenue"].median())
    daily["revenue_lag_7"] = daily["daily_revenue"].shift(7).fillna(daily["daily_revenue"].median())
    daily["revenue_lag_14"] = daily["daily_revenue"].shift(14).fillna(daily["daily_revenue"].median())
    daily["revenue_lag_30"] = daily["daily_revenue"].shift(30).fillna(daily["daily_revenue"].median())

    # Rolling Window Statistics (SMA and Volatility)
    daily["revenue_rolling_mean_7"] = (
        daily["daily_revenue"].rolling(window=7, min_periods=1).mean().round(2)
    )
    daily["revenue_rolling_mean_30"] = (
        daily["daily_revenue"].rolling(window=30, min_periods=1).mean().round(2)
    )
    daily["revenue_rolling_std_7"] = (
        daily["daily_revenue"].rolling(window=7, min_periods=1).std().fillna(0.0).round(2)
    )
    daily["revenue_rolling_std_30"] = (
        daily["daily_revenue"].rolling(window=30, min_periods=1).std().fillna(0.0).round(2)
    )

    # Calendar & Cyclical Features
    date_series = pd.to_datetime(daily["date"])
    daily["day_of_week"] = date_series.dt.dayofweek
    daily["day_of_month"] = date_series.dt.day
    daily["month"] = date_series.dt.month
    daily["is_weekend"] = daily["day_of_week"].isin([5, 6]).astype(int)

    # Trigonometric Cyclical Encoding
    # Preserves circular distance: Day 6 (Sun) is adjacent to Day 0 (Mon)
    daily["day_of_week_sin"] = np.sin(2 * np.pi * daily["day_of_week"] / 7.0).round(4)
    daily["day_of_week_cos"] = np.cos(2 * np.pi * daily["day_of_week"] / 7.0).round(4)
    daily["month_sin"] = np.sin(2 * np.pi * daily["month"] / 12.0).round(4)
    daily["month_cos"] = np.cos(2 * np.pi * daily["month"] / 12.0).round(4)

    # Catalog Items
    catalog = [
        FeatureCatalogItem(
            name="daily_revenue",
            feature_group="Time-Series Target",
            data_type="float",
            description="Daily aggregated gross revenue across all transactions",
            downstream_model="Sales Forecasting (ARIMA / Prophet / XGBoost)",
            mean_value=float(daily["daily_revenue"].mean()),
            min_value=float(daily["daily_revenue"].min()),
            max_value=float(daily["daily_revenue"].max()),
        ),
        FeatureCatalogItem(
            name="revenue_lag_7",
            feature_group="Time-Series Lags",
            data_type="float",
            description="Revenue from exactly 7 days prior (captures weekly recurring seasonality)",
            downstream_model="Autoregressive Forecasting",
            mean_value=float(daily["revenue_lag_7"].mean()),
            min_value=float(daily["revenue_lag_7"].min()),
            max_value=float(daily["revenue_lag_7"].max()),
        ),
        FeatureCatalogItem(
            name="revenue_rolling_mean_7",
            feature_group="Time-Series Rolling",
            data_type="float",
            description="7-day Simple Moving Average (SMA) smoothing out day-of-week noise",
            downstream_model="Trend Analysis & Momentum",
            mean_value=float(daily["revenue_rolling_mean_7"].mean()),
            min_value=float(daily["revenue_rolling_mean_7"].min()),
            max_value=float(daily["revenue_rolling_mean_7"].max()),
        ),
        FeatureCatalogItem(
            name="revenue_rolling_std_7",
            feature_group="Time-Series Rolling",
            data_type="float",
            description="7-day rolling standard deviation measuring short-term revenue volatility",
            downstream_model="Anomaly Detection & Risk Bounds",
            mean_value=float(daily["revenue_rolling_std_7"].mean()),
            min_value=float(daily["revenue_rolling_std_7"].min()),
            max_value=float(daily["revenue_rolling_std_7"].max()),
        ),
        FeatureCatalogItem(
            name="day_of_week_sin",
            feature_group="Calendar & Seasonality",
            data_type="float",
            description="Sine component of cyclical day-of-week encoding [-1.0, 1.0]",
            downstream_model="Gradient Boosted Forecasting",
            mean_value=float(daily["day_of_week_sin"].mean()),
            min_value=float(daily["day_of_week_sin"].min()),
            max_value=float(daily["day_of_week_sin"].max()),
        ),
    ]

    return daily, catalog


async def generate_dataset_features(
    dataset_id: str,
    organization_id: str,
    db: AsyncIOMotorDatabase,
) -> FeatureEngineeringResponse:
    """Generate both customer-level and time-series feature tables for a dataset in MongoDB."""
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
    cleaned_file_path = col_meta.get("cleaned_file_path")
    file_to_load = cleaned_file_path if cleaned_file_path and os.path.exists(cleaned_file_path) else dataset.file_path

    df = load_dataset_as_dataframe(file_to_load, dataset.file_type)

    mappings = dataset.column_mappings or {}
    if not mappings:
        mapping_resp = await get_dataset_mapping_suggestions(dataset_id, organization_id, db)
        mappings = {m.canonical_field: m.mapped_column for m in mapping_resp.mappings if m.mapped_column}

    date_col = mappings.get("order_date")
    revenue_col = mappings.get("revenue")
    cust_id_col = mappings.get("customer_id")
    order_id_col = mappings.get("order_id")
    cat_col = mappings.get("category")

    catalog_all: List[FeatureCatalogItem] = []
    cust_summary: Optional[CustomerFeatureSummary] = None
    ts_summary: Optional[TimeSeriesFeatureSummary] = None

    base_dir = os.path.dirname(dataset.file_path)

    # 1. Customer Features
    if cust_id_col and date_col and revenue_col and cust_id_col in df.columns:
        cust_df, cust_cat = compute_customer_rfm_features(
            df=df,
            customer_id_col=cust_id_col,
            date_col=date_col,
            revenue_col=revenue_col,
            order_id_col=order_id_col,
            category_col=cat_col,
        )
        catalog_all.extend(cust_cat)
        cust_features_path = os.path.join(base_dir, f"{dataset.id}_customer_features.csv")
        cust_df.to_csv(cust_features_path, index=False)

        multi_pct = float((cust_df["frequency"] > 1).sum() / len(cust_df) * 100) if len(cust_df) > 0 else 0.0
        sample_records = cust_df.head(5).to_dict(orient="records")
        for rec in sample_records:
            for k, v in rec.items():
                if isinstance(v, (datetime, pd.Timestamp)):
                    rec[k] = v.isoformat()

        cust_summary = CustomerFeatureSummary(
            total_customers=len(cust_df),
            avg_recency_days=float(cust_df["recency_days"].mean()),
            avg_frequency=float(cust_df["frequency"].mean()),
            avg_monetary_spend=float(cust_df["monetary_total"].mean()),
            avg_order_value=float(cust_df["avg_order_value"].mean()),
            multi_order_customer_pct=round(multi_pct, 1),
            features_file_path=cust_features_path,
            sample_records=sample_records,
        )

    # 2. Time-Series Features
    if date_col and revenue_col and date_col in df.columns and revenue_col in df.columns:
        ts_df, ts_cat = compute_timeseries_features(
            df=df,
            date_col=date_col,
            revenue_col=revenue_col,
            order_id_col=order_id_col,
        )
        catalog_all.extend(ts_cat)
        ts_features_path = os.path.join(base_dir, f"{dataset.id}_timeseries_features.csv")
        ts_df.to_csv(ts_features_path, index=False)

        sample_ts = ts_df.head(5).to_dict(orient="records")
        for rec in sample_ts:
            for k, v in rec.items():
                if hasattr(v, "isoformat"):
                    rec[k] = v.isoformat()
                elif isinstance(v, (np.floating, float)):
                    rec[k] = round(float(v), 2)

        ts_summary = TimeSeriesFeatureSummary(
            total_days=len(ts_df),
            start_date=str(ts_df["date"].min()),
            end_date=str(ts_df["date"].max()),
            avg_daily_revenue=float(ts_df["daily_revenue"].mean()),
            features_file_path=ts_features_path,
            sample_records=sample_ts,
        )

    generated_at = datetime.utcnow().isoformat()

    # Save metadata in MongoDB
    col_meta["features_summary"] = {
        "dataset_id": str(dataset.id),
        "has_customer_features": cust_summary is not None,
        "has_timeseries_features": ts_summary is not None,
        "total_engineered_features": len(catalog_all),
        "generated_at": generated_at,
    }

    await db.datasets.update_one(
        {"$or": [{"id": dataset.id}, {"_id": dataset.id}]},
        {"$set": {
            "column_metadata": col_meta,
            "updated_at": datetime.utcnow(),
        }}
    )

    return FeatureEngineeringResponse(
        dataset_id=str(dataset.id),
        customer_summary=cust_summary,
        timeseries_summary=ts_summary,
        catalog=catalog_all,
        generated_at=generated_at,
    )
