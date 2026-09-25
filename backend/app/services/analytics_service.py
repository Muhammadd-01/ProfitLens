"""Executive Analytics and Business Intelligence Service.

Computes deterministic, model-grade executive business KPIs, period-over-period growth rates,
daily/monthly revenue trajectories, Pareto 80/20 category distributions, and top product performances.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.schemas.analytics import (
    KPIData,
    RevenueTimeSeries,
    CategoryRevenue,
    ProductPerformanceSummary,
    ObservationPeriod,
    ExecutiveDashboardSummary,
)
from app.services.cleaning_service import load_dataset_as_dataframe
from app.services.mapping_service import get_dataset_mapping_suggestions


def calculate_pct_change(current: float, prior: float) -> Optional[float]:
    """Calculate relative percentage change with epsilon zero-division guard."""
    if prior is None or prior <= 0.0:
        return None
    return round(((current - prior) / prior) * 100.0, 1)


def compute_executive_kpis(
    df: pd.DataFrame,
    date_col: str,
    revenue_col: str,
    order_id_col: Optional[str] = None,
    customer_id_col: Optional[str] = None,
) -> Tuple[KPIData, ObservationPeriod]:
    """Calculate executive KPIs with Period-over-Period comparisons."""
    total_rev = float(df[revenue_col].sum())
    total_orders = int(df[order_id_col].nunique()) if order_id_col and order_id_col in df.columns else len(df)
    total_customers = int(df[customer_id_col].nunique()) if customer_id_col and customer_id_col in df.columns else total_orders
    aov = round(total_rev / max(1, total_orders), 2)

    # Observation span
    min_date = df[date_col].min()
    max_date = df[date_col].max()
    span_days = int((max_date - min_date).days)

    obs_period = ObservationPeriod(
        start_date=min_date.strftime("%Y-%m-%d"),
        end_date=max_date.strftime("%Y-%m-%d"),
        total_days=span_days,
    )

    # Period-over-period calculation
    # Using symmetric calendar days to avoid off-by-one and length mismatch bias
    rev_change = None
    orders_change = None
    cust_change = None
    aov_change = None

    unique_dates = sorted(df[date_col].dt.date.unique())
    num_unique = len(unique_dates)

    if num_unique >= 14:
        period_length = min(30, num_unique // 2)
        curr_dates = set(unique_dates[-period_length:])
        prior_dates = set(unique_dates[-2 * period_length : -period_length])

        date_series = df[date_col].dt.date
        curr_df = df[date_series.isin(curr_dates)]
        prior_df = df[date_series.isin(prior_dates)]

        if len(curr_df) > 0 and len(prior_df) > 0:
            curr_rev = float(curr_df[revenue_col].sum())
            prior_rev = float(prior_df[revenue_col].sum())
            rev_change = calculate_pct_change(curr_rev, prior_rev)

            curr_ord = int(curr_df[order_id_col].nunique()) if order_id_col and order_id_col in curr_df.columns else len(curr_df)
            prior_ord = int(prior_df[order_id_col].nunique()) if order_id_col and order_id_col in prior_df.columns else len(prior_df)
            orders_change = calculate_pct_change(float(curr_ord), float(prior_ord))

            curr_cust = int(curr_df[customer_id_col].nunique()) if customer_id_col and customer_id_col in curr_df.columns else curr_ord
            prior_cust = int(prior_df[customer_id_col].nunique()) if customer_id_col and customer_id_col in prior_df.columns else prior_ord
            customers_change = calculate_pct_change(float(curr_cust), float(prior_cust))

            curr_aov = curr_rev / max(1, curr_ord)
            prior_aov = prior_rev / max(1, prior_ord)
            aov_change = calculate_pct_change(curr_aov, prior_aov)

    kpis = KPIData(
        total_revenue=round(total_rev, 2),
        total_orders=total_orders,
        total_customers=total_customers,
        avg_order_value=aov,
        revenue_change_pct=rev_change,
        orders_change_pct=orders_change,
        customers_change_pct=customers_change,
        aov_change_pct=aov_change,
    )

    return kpis, obs_period


def compute_revenue_timeseries(
    df: pd.DataFrame,
    date_col: str,
    revenue_col: str,
    order_id_col: Optional[str] = None,
) -> Tuple[List[RevenueTimeSeries], List[RevenueTimeSeries]]:
    """Generate daily and monthly revenue trajectories with cumulative aggregates."""
    work_df = df.copy()
    work_df["day"] = work_df[date_col].dt.date
    work_df["month"] = work_df[date_col].dt.strftime("%Y-%m")

    # 1. Daily Aggregation
    if order_id_col and order_id_col in work_df.columns:
        daily_agg = work_df.groupby("day").agg(
            revenue=(revenue_col, "sum"),
            orders=(order_id_col, "nunique"),
        )
    else:
        daily_agg = work_df.groupby("day").agg(
            revenue=(revenue_col, "sum"),
            orders=(revenue_col, "count"),
        )

    # Reindex to full daily range
    min_date = daily_agg.index.min()
    max_date = daily_agg.index.max()
    full_idx = pd.date_range(start=min_date, end=max_date, freq="D").date
    daily_agg = daily_agg.reindex(full_idx, fill_value=0.0)
    daily_agg.index.name = "date"
    daily_agg = daily_agg.reset_index()

    daily_agg["cumulative_revenue"] = daily_agg["revenue"].cumsum().round(2)

    daily_series: List[RevenueTimeSeries] = []
    for _, row in daily_agg.iterrows():
        daily_series.append(
            RevenueTimeSeries(
                date=str(row["date"]),
                revenue=round(float(row["revenue"]), 2),
                orders=int(row["orders"]),
                cumulative_revenue=round(float(row["cumulative_revenue"]), 2),
            )
        )

    # 2. Monthly Aggregation
    if order_id_col and order_id_col in work_df.columns:
        monthly_agg = work_df.groupby("month").agg(
            revenue=(revenue_col, "sum"),
            orders=(order_id_col, "nunique"),
        ).reset_index()
    else:
        monthly_agg = work_df.groupby("month").agg(
            revenue=(revenue_col, "sum"),
            orders=(revenue_col, "count"),
        ).reset_index()

    monthly_agg = monthly_agg.sort_values("month")
    monthly_agg["cumulative_revenue"] = monthly_agg["revenue"].cumsum().round(2)

    monthly_series: List[RevenueTimeSeries] = []
    for _, row in monthly_agg.iterrows():
        monthly_series.append(
            RevenueTimeSeries(
                date=str(row["month"]),
                revenue=round(float(row["revenue"]), 2),
                orders=int(row["orders"]),
                cumulative_revenue=round(float(row["cumulative_revenue"]), 2),
            )
        )

    return daily_series, monthly_series


def compute_category_breakdown(
    df: pd.DataFrame,
    category_col: Optional[str],
    revenue_col: str,
    order_id_col: Optional[str] = None,
) -> List[CategoryRevenue]:
    """Calculate category revenue share with Pareto 80/20 classification."""
    total_rev = float(df[revenue_col].sum())
    if total_rev <= 0:
        return []

    col = category_col if category_col and category_col in df.columns else None

    if col:
        if order_id_col and order_id_col in df.columns:
            cat_df = df.groupby(col).agg(
                revenue=(revenue_col, "sum"),
                orders=(order_id_col, "nunique"),
            ).reset_index()
        else:
            cat_df = df.groupby(col).agg(
                revenue=(revenue_col, "sum"),
                orders=(revenue_col, "count"),
            ).reset_index()
        cat_df = cat_df.rename(columns={col: "category"})
    else:
        cat_df = pd.DataFrame([{
            "category": "All Products",
            "revenue": total_rev,
            "orders": len(df),
        }])

    # Sort descending
    cat_df = cat_df.sort_values("revenue", ascending=False).reset_index(drop=True)
    cat_df["percentage"] = ((cat_df["revenue"] / total_rev) * 100.0).round(1)
    cat_df["cumulative_percentage"] = cat_df["percentage"].cumsum().round(1)

    results: List[CategoryRevenue] = []
    for _, row in cat_df.iterrows():
        # Pareto 80 condition: categories whose start point is under 80%
        prior_cum = float(row["cumulative_percentage"] - row["percentage"])
        is_pareto = prior_cum < 80.0

        results.append(
            CategoryRevenue(
                category=str(row["category"]),
                revenue=round(float(row["revenue"]), 2),
                orders=int(row["orders"]),
                percentage=float(row["percentage"]),
                cumulative_percentage=float(row["cumulative_percentage"]),
                is_pareto_80=is_pareto,
            )
        )

    return results


def compute_top_products(
    df: pd.DataFrame,
    product_id_col: Optional[str],
    revenue_col: str,
    quantity_col: Optional[str] = None,
    order_id_col: Optional[str] = None,
    top_n: int = 10,
) -> List[ProductPerformanceSummary]:
    """Calculate performance metrics for top products."""
    total_rev = float(df[revenue_col].sum())
    if total_rev <= 0:
        return []

    col = product_id_col if product_id_col and product_id_col in df.columns else None
    if not col:
        return []

    agg_dict = {
        revenue_col: "sum",
    }
    if quantity_col and quantity_col in df.columns:
        agg_dict[quantity_col] = "sum"
    if order_id_col and order_id_col in df.columns:
        agg_dict[order_id_col] = "nunique"

    prod_df = df.groupby(col).agg(agg_dict).reset_index()

    prod_df["revenue"] = prod_df[revenue_col].round(2)
    prod_df["units_sold"] = (
        prod_df[quantity_col].astype(int) if quantity_col and quantity_col in prod_df.columns else 1
    )
    prod_df["order_count"] = (
        prod_df[order_id_col].astype(int) if order_id_col and order_id_col in prod_df.columns else 1
    )
    prod_df["avg_price"] = (prod_df["revenue"] / prod_df["units_sold"].replace(0, 1)).round(2)
    prod_df["percentage_of_total"] = ((prod_df["revenue"] / total_rev) * 100.0).round(2)

    top_df = prod_df.sort_values("revenue", ascending=False).head(top_n)

    results: List[ProductPerformanceSummary] = []
    for _, row in top_df.iterrows():
        results.append(
            ProductPerformanceSummary(
                product_id=str(row[col]),
                revenue=float(row["revenue"]),
                units_sold=int(row["units_sold"]),
                avg_price=float(row["avg_price"]),
                order_count=int(row["order_count"]),
                percentage_of_total=float(row["percentage_of_total"]),
            )
        )

    return results


async def generate_executive_dashboard(
    dataset_id: str,
    organization_id: str,
    db: AsyncSession,
) -> ExecutiveDashboardSummary:
    """Generate complete Executive Dashboard summary for a dataset."""
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == uuid.UUID(dataset_id),
            Dataset.organization_id == uuid.UUID(organization_id),
        )
    )
    dataset = result.scalar_one_or_none()
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
    prod_col = mappings.get("product_id")
    qty_col = mappings.get("quantity")

    if not date_col or not revenue_col or date_col not in df.columns or revenue_col not in df.columns:
        raise ValueError("Dataset requires mapped 'order_date' and 'revenue' columns to calculate analytics")

    # Ensure types
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce", utc=True)
    df = df.dropna(subset=[date_col])
    df[revenue_col] = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0.0)

    # 1. KPIs
    kpis, obs_period = compute_executive_kpis(
        df=df,
        date_col=date_col,
        revenue_col=revenue_col,
        order_id_col=order_id_col,
        customer_id_col=cust_id_col,
    )

    # 2. Revenue Time Series
    daily_ts, monthly_ts = compute_revenue_timeseries(
        df=df,
        date_col=date_col,
        revenue_col=revenue_col,
        order_id_col=order_id_col,
    )

    # 3. Category Breakdown
    categories = compute_category_breakdown(
        df=df,
        category_col=cat_col,
        revenue_col=revenue_col,
        order_id_col=order_id_col,
    )

    # 4. Top Products
    top_products = compute_top_products(
        df=df,
        product_id_col=prod_col,
        revenue_col=revenue_col,
        quantity_col=qty_col,
        order_id_col=order_id_col,
        top_n=10,
    )

    return ExecutiveDashboardSummary(
        dataset_id=str(dataset.id),
        kpis=kpis,
        time_series_daily=daily_ts,
        time_series_monthly=monthly_ts,
        categories=categories,
        top_products=top_products,
        observation_period=obs_period,
    )
