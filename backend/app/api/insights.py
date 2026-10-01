"""Executive Business Insights API Endpoints."""

from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.dependencies import get_current_user, get_organization_id
from app.models.user import User
from app.schemas.insights import (
    InsightFeedResponse,
    InsightDismissRequest,
)
from app.services.insights_service import (
    generate_executive_insights,
    dismiss_insight_item,
)

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/{dataset_id}/feed", response_model=InsightFeedResponse)
async def get_insights_feed(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Retrieve prioritized executive business insights feed."""
    try:
        return await generate_executive_insights(
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
            detail=f"Insights retrieval failed: {str(e)}",
        )


@router.post("/{dataset_id}/generate", response_model=InsightFeedResponse)
async def trigger_insights_generation(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Re-evaluate all business rules and generate updated executive insights."""
    try:
        return await generate_executive_insights(
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
            detail=f"Insights generation failed: {str(e)}",
        )


@router.patch("/{dataset_id}/{insight_id}/dismiss")
async def dismiss_insight(
    dataset_id: str,
    insight_id: str,
    request: Optional[InsightDismissRequest] = None,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Dismiss or restore a specific executive insight card."""
    is_dismissed = request.dismissed if request else True
    try:
        await dismiss_insight_item(
            dataset_id=dataset_id,
            organization_id=organization_id,
            insight_id=insight_id,
            dismissed=is_dismissed,
            db=db,
        )
        return {"status": "success", "insight_id": insight_id, "dismissed": is_dismissed}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Insight dismissal failed: {str(e)}",
        )
