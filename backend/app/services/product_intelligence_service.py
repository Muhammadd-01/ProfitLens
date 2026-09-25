"""Product Performance & Intelligence Service.

Computes SKU-level performance metrics, Pareto 80/20 cumulative distribution,
Boston Consulting Group (BCG) Growth-Share Matrix classifications (Stars, Cash Cows,
Question Marks, Dogs), return rate diagnostics, and actionable merchandising recommendations.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.schemas.analytics import (
    ProductBCGItem,
    ProductParetoPoint,
    ProductBCGDistribution,
    ProductIntelligenceResponse,
)
from app.services.cleaning_service import load_dataset_as_dataframe
from app.services.mapping_service import get_dataset_mapping_suggestions


def compute_product_metrics(
    df: pd.DataFrame,
    product_id_col: str,
    revenue_col: str,
    date_col: str,
    quantity_col: Optional[str] = None,
    category_col: Optional[str] = None,
    product_name_col: Optional[str] = None,
    status_col: Optional[str] = None,
) -> pd.DataFrame:
    """Aggregates product performance across revenue, units, orders, and returns."""
    data = df.copy()
    data[revenue_col] = pd.to_numeric(data[revenue_col], errors="coerce").fillna(0.0)
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce", utc=True)
    data = data.dropna(subset=[product_id_col, revenue_col, date_col])

    if quantity_col and quantity_col in data.columns:
        data["units"] = pd.to_numeric(data[quantity_col], errors="coerce").fillna(1.0)
    else:
        data["units"] = 1.0

    # Group by product
    group_cols = [product_id_col]
    if category_col and category_col in data.columns:
        group_cols.append(category_col)
    if product_name_col and product_name_col in data.columns:
        group_cols.append(product_name_col)

    grouped = data.groupby(group_cols).agg(
        revenue=(revenue_col, "sum"),
        units_sold=("units", "sum"),
        order_count=(product_id_col, "count"),
    ).reset_index()

    # Average selling price
    grouped["avg_price"] = (grouped["revenue"] / np.maximum(1.0, grouped["units_sold"])).round(2)

    # Return rate calculation if status column exists
    if status_col and status_col in data.columns:
        return_mask = data[status_col].astype(str).str.lower().str.contains("return|refund|cancel")
        returns_by_prod = data[return_mask].groupby(product_id_col).size().to_dict()
        grouped["return_count"] = grouped[product_id_col].map(returns_by_prod).fillna(0)
        grouped["return_rate_pct"] = ((grouped["return_count"] / np.maximum(1.0, grouped["order_count"])) * 100.0).round(1)
    else:
        grouped["return_rate_pct"] = None

    return grouped


def compute_product_growth_rates(
    df: pd.DataFrame,
    product_id_col: str,
    revenue_col: str,
    date_col: str,
) -> Dict[str, float]:
    """Computes period-over-period sales growth rate (%) for each SKU."""
    data = df.copy()
    data[revenue_col] = pd.to_numeric(data[revenue_col], errors="coerce").fillna(0.0)
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce", utc=True)
    data = data.dropna(subset=[product_id_col, revenue_col, date_col])

    min_date = data[date_col].min()
    max_date = data[date_col].max()
    mid_date = min_date + (max_date - min_date) / 2

    prior_df = data[data[date_col] < mid_date]
    recent_df = data[data[date_col] >= mid_date]

    prior_rev = prior_df.groupby(product_id_col)[revenue_col].sum().to_dict()
    recent_rev = recent_df.groupby(product_id_col)[revenue_col].sum().to_dict()

    growth_rates: Dict[str, float] = {}
    all_products = set(data[product_id_col].unique())

    for pid in all_products:
        p_prior = float(prior_rev.get(pid, 0.0))
        p_recent = float(recent_rev.get(pid, 0.0))

        if p_prior > 0:
            growth = ((p_recent - p_prior) / p_prior) * 100.0
        elif p_recent > 0:
            growth = 100.0  # New product surge
        else:
            growth = 0.0

        growth_rates[str(pid)] = round(float(np.clip(growth, -100.0, 500.0)), 1)

    return growth_rates


def classify_bcg_quadrants(
    products_df: pd.DataFrame,
    growth_rates: Dict[str, float],
    product_id_col: str,
    category_col: Optional[str] = None,
) -> pd.DataFrame:
    """Classifies products into BCG Matrix quadrants: Stars, Cash Cows, Question Marks, Dogs."""
    df = products_df.copy()
    df["growth_rate_pct"] = df[product_id_col].astype(str).map(growth_rates).fillna(0.0)

    # Relative Market Share: product revenue / max product revenue in category (or whole catalog)
    if category_col and category_col in df.columns:
        cat_max = df.groupby(category_col)["revenue"].transform("max")
        df["relative_market_share"] = (df["revenue"] / np.maximum(1.0, cat_max)).round(2)
    else:
        catalog_max = df["revenue"].max() if len(df) > 0 else 1.0
        df["relative_market_share"] = (df["revenue"] / max(1.0, catalog_max)).round(2)

    # Threshold benchmarks
    median_growth = float(df["growth_rate_pct"].median()) if len(df) > 0 else 0.0
    growth_threshold = max(0.0, median_growth)
    share_threshold = 0.40  # 40% or higher of category leader is dominant share

    bcg_classes = []
    recommendations = []

    for _, row in df.iterrows():
        rms = float(row["relative_market_share"])
        growth = float(row["growth_rate_pct"])

        if rms >= share_threshold and growth >= growth_threshold:
            bcg = "star"
            rec = "High-growth category leader. Reinvest ad spend and maintain healthy inventory buffers to defend dominant position."
        elif rms >= share_threshold and growth < growth_threshold:
            bcg = "cash_cow"
            rec = "High-share staple generator. Harvest operating margins with minimal marketing overhead; protect price points."
        elif rms < share_threshold and growth >= growth_threshold:
            bcg = "question_mark"
            rec = "Fast-growing niche product with low market share. Run targeted promotions to scale volume into a Star, or divest if ad ROI is poor."
        else:
            bcg = "dog"
            rec = "Low market share and sluggish growth rate. Consider discounting to clear warehouse space and reallocating capital to Stars."

        bcg_classes.append(bcg)
        recommendations.append(rec)

    df["bcg_category"] = bcg_classes
    df["recommendation"] = recommendations
    return df


def compute_product_pareto_curve(
    products_df: pd.DataFrame,
    product_id_col: str,
    product_name_col: Optional[str] = None,
) -> Tuple[pd.DataFrame, List[ProductParetoPoint]]:
    """Calculates cumulative Pareto 80/20 distribution and assigns ABC stratification classes."""
    df = products_df.sort_values("revenue", ascending=False).reset_index(drop=True)
    total_rev = float(df["revenue"].sum())

    if total_rev <= 0:
        df["cumulative_revenue_pct"] = 0.0
        df["pareto_class"] = "C"
        return df, []

    df["rank"] = df.index + 1
    df["cumulative_revenue"] = df["revenue"].cumsum().round(2)
    df["cumulative_revenue_pct"] = ((df["cumulative_revenue"] / total_rev) * 100.0).round(1)

    pareto_classes = []
    points: List[ProductParetoPoint] = []

    for _, row in df.iterrows():
        cum_pct = float(row["cumulative_revenue_pct"])
        prev_pct = cum_pct - ((float(row["revenue"]) / total_rev) * 100.0)

        if prev_pct < 80.0:
            p_class = "A"
            in_top_80 = True
        elif prev_pct < 95.0:
            p_class = "B"
            in_top_80 = False
        else:
            p_class = "C"
            in_top_80 = False

        pareto_classes.append(p_class)

        p_name = str(row[product_name_col]) if product_name_col and product_name_col in row and pd.notna(row[product_name_col]) else str(row[product_id_col])
        points.append(
            ProductParetoPoint(
                rank=int(row["rank"]),
                product_id=str(row[product_id_col]),
                product_name=p_name,
                revenue=round(float(row["revenue"]), 2),
                cumulative_revenue=round(float(row["cumulative_revenue"]), 2),
                cumulative_percentage=cum_pct,
                is_in_top_80=in_top_80,
            )
        )

    df["pareto_class"] = pareto_classes
    return df, points


async def generate_product_intelligence(
    dataset_id: str,
    organization_id: str,
    db: Optional[AsyncSession] = None,
) -> ProductIntelligenceResponse:
    """End-to-end product performance engine: metrics, BCG matrix, Pareto distribution, and recommendations."""
    if db is None:
        raise ValueError("Database session required")

    result = await db.execute(
        select(Dataset).where(
            Dataset.id == uuid.UUID(dataset_id),
            Dataset.organization_id == uuid.UUID(organization_id),
        )
    )
    dataset = result.scalar_one_or_none()
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

    prod_col = mappings.get("product_id")
    rev_col = mappings.get("revenue")
    date_col = mappings.get("order_date")
    qty_col = mappings.get("quantity")
    cat_col = mappings.get("category")
    name_col = mappings.get("product_name") or prod_col
    status_col = mappings.get("status")

    if not prod_col or not rev_col or not date_col:
        raise ValueError("Product intelligence requires mapped product_id, revenue, and order_date columns.")

    # 1. Aggregate metrics
    metrics_df = compute_product_metrics(
        df=raw_df,
        product_id_col=prod_col,
        revenue_col=rev_col,
        date_col=date_col,
        quantity_col=qty_col,
        category_col=cat_col,
        product_name_col=name_col if name_col != prod_col else None,
        status_col=status_col,
    )

    if len(metrics_df) == 0:
        raise ValueError("No valid product transactions found in dataset.")

    # 2. Compute period-over-period growth rates
    growth_dict = compute_product_growth_rates(
        df=raw_df,
        product_id_col=prod_col,
        revenue_col=rev_col,
        date_col=date_col,
    )

    # 3. Classify into BCG matrix quadrants
    bcg_df = classify_bcg_quadrants(
        products_df=metrics_df,
        growth_rates=growth_dict,
        product_id_col=prod_col,
        category_col=cat_col,
    )

    # 4. Compute Pareto 80/20 curve and ABC classes
    pareto_df, pareto_points = compute_product_pareto_curve(
        products_df=bcg_df,
        product_id_col=prod_col,
        product_name_col=name_col if name_col != prod_col else None,
    )

    # 5. Build quadrant distributions
    stars = pareto_df[pareto_df["bcg_category"] == "star"]
    cows = pareto_df[pareto_df["bcg_category"] == "cash_cow"]
    qms = pareto_df[pareto_df["bcg_category"] == "question_mark"]
    dogs = pareto_df[pareto_df["bcg_category"] == "dog"]

    distribution = ProductBCGDistribution(
        stars_count=len(stars),
        cash_cows_count=len(cows),
        question_marks_count=len(qms),
        dogs_count=len(dogs),
        total_products=len(pareto_df),
        stars_revenue=round(float(stars["revenue"].sum()), 2),
        cash_cows_revenue=round(float(cows["revenue"].sum()), 2),
        question_marks_revenue=round(float(qms["revenue"].sum()), 2),
        dogs_revenue=round(float(dogs["revenue"].sum()), 2),
    )

    # 6. Build product items list
    items: List[ProductBCGItem] = []
    for _, row in pareto_df.iterrows():
        p_name = str(row[name_col]) if name_col and name_col in row and pd.notna(row[name_col]) else str(row[prod_col])
        p_cat = str(row[cat_col]) if cat_col and cat_col in row and pd.notna(row[cat_col]) else "General"
        items.append(
            ProductBCGItem(
                product_id=str(row[prod_col]),
                product_name=p_name,
                category=p_cat,
                revenue=round(float(row["revenue"]), 2),
                units_sold=int(row["units_sold"]),
                avg_price=float(row["avg_price"]),
                order_count=int(row["order_count"]),
                relative_market_share=float(row["relative_market_share"]),
                growth_rate_pct=float(row["growth_rate_pct"]),
                bcg_category=str(row["bcg_category"]),
                pareto_class=str(row["pareto_class"]),
                cumulative_revenue_pct=float(row["cumulative_revenue_pct"]),
                return_rate_pct=float(row["return_rate_pct"]) if pd.notna(row.get("return_rate_pct")) else None,
                recommendation=str(row["recommendation"]),
            )
        )

    # Top category
    top_cat = None
    if cat_col and cat_col in raw_df.columns:
        cat_sums = raw_df.groupby(cat_col)[rev_col].sum()
        if len(cat_sums) > 0:
            top_cat = str(cat_sums.idxmax())

    total_rev = round(float(pareto_df["revenue"].sum()), 2)
    total_units = int(pareto_df["units_sold"].sum())
    avg_prod_rev = round(total_rev / max(1, len(pareto_df)), 2)
    gen_time = datetime.utcnow().isoformat()

    # Cache results in dataset metadata
    col_meta["product_intelligence"] = {
        "dataset_id": str(dataset.id),
        "total_products": len(pareto_df),
        "total_revenue": total_rev,
        "distribution": distribution.model_dump(),
        "generated_at": gen_time,
    }
    dataset.column_metadata = col_meta
    await db.commit()

    return ProductIntelligenceResponse(
        dataset_id=str(dataset.id),
        total_products=len(pareto_df),
        total_revenue=total_rev,
        total_units_sold=total_units,
        avg_product_revenue=avg_prod_rev,
        top_performing_category=top_cat,
        bcg_distribution=distribution,
        pareto_points=pareto_points,
        products=items,
        generated_at=gen_time,
    )
