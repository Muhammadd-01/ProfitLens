"""Executive Business Intelligence & KPI Analytics API Endpoints."""

from __future__ import annotations

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_organization_id
from app.models.user import User
from app.schemas.analytics import (
    KPIData,
    RevenueTimeSeries,
    CategoryRevenue,
    ProductPerformanceSummary,
    ExecutiveDashboardSummary,
    ProductIntelligenceResponse,
)
from app.services.analytics_service import generate_executive_dashboard
from app.services.product_intelligence_service import generate_product_intelligence

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/{dataset_id}/summary", response_model=ExecutiveDashboardSummary)
async def get_dashboard_summary(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get complete Executive Dashboard packet: KPIs, daily & monthly timeseries, categories, and products."""
    try:
        return await generate_executive_dashboard(
            dataset_id=dataset_id,
            organization_id=organization_id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics calculation failed: {str(e)}",
        )


@router.get("/{dataset_id}/kpis", response_model=KPIData)
async def get_kpis(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get high-level executive KPIs with period-over-period percentage comparisons."""
    summary = await get_dashboard_summary(dataset_id, organization_id, current_user, db)
    return summary.kpis


@router.get("/{dataset_id}/revenue-timeseries", response_model=List[RevenueTimeSeries])
async def get_timeseries(
    dataset_id: str,
    granularity: str = Query("daily", enum=["daily", "monthly"]),
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get historical revenue trajectory with cumulative totals."""
    summary = await get_dashboard_summary(dataset_id, organization_id, current_user, db)
    if granularity == "monthly":
        return summary.time_series_monthly
    return summary.time_series_daily


@router.get("/{dataset_id}/categories", response_model=List[CategoryRevenue])
async def get_category_breakdown(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get category revenue contributions with Pareto 80/20 tagging."""
    summary = await get_dashboard_summary(dataset_id, organization_id, current_user, db)
    return summary.categories


@router.get("/{dataset_id}/products", response_model=List[ProductPerformanceSummary])
async def get_top_products(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get top performing revenue-generating products."""
    summary = await get_dashboard_summary(dataset_id, organization_id, current_user, db)
    return summary.top_products


@router.get("/{dataset_id}/products/intelligence", response_model=ProductIntelligenceResponse)
async def get_product_intelligence(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full product performance intelligence: BCG growth-share matrix, Pareto 80/20 distribution, and SKU actions."""
    try:
        return await generate_product_intelligence(
            dataset_id=dataset_id,
            organization_id=organization_id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Product intelligence calculation failed: {str(e)}",
        )

