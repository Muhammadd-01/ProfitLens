"""Machine Learning API Endpoints (Customer Segmentation, Churn, Forecasting, Anomaly Detection)."""

from __future__ import annotations

from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_organization_id
from app.models.user import User
from app.models.dataset import Dataset
from app.schemas.ml import (
    SegmentationTrainRequest,
    SegmentationTrainResponse,
    ChurnTrainRequest,
    ChurnOverviewResponse,
    ChurnCustomerListResponse,
    ForecastTrainRequest,
    ForecastResponse,
    AnomalyItem,
    AnomalyDetectRequest,
    AnomalyOverviewResponse,
    AnomalyReviewRequest,
    SentimentOverviewResponse,
)
from app.services.segmentation_service import run_customer_segmentation
from app.services.churn_service import (
    run_customer_churn_prediction,
    get_churn_customers_paginated,
)
from app.services.forecast_service import run_sales_forecasting
from app.services.anomaly_service import (
    run_transaction_anomaly_detection,
    get_or_run_anomalies,
    review_anomaly_record,
)
from app.services.sentiment_service import run_customer_sentiment_analysis

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


@router.post("/{dataset_id}/segmentation/train", response_model=SegmentationTrainResponse)
async def train_segmentation(
    dataset_id: str,
    request: Optional[SegmentationTrainRequest] = None,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fit or refit K-Means customer segmentation with optimal or specified k."""
    k_val = request.k if request else None
    try:
        return await run_customer_segmentation(
            dataset_id=dataset_id,
            organization_id=organization_id,
            k_clusters=k_val,
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
            detail=f"Customer segmentation failed: {str(e)}",
        )


@router.get("/{dataset_id}/segmentation/results", response_model=SegmentationTrainResponse)
async def get_segmentation_results(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve existing customer segmentation results or trigger initial run."""
    try:
        return await run_customer_segmentation(
            dataset_id=dataset_id,
            organization_id=organization_id,
            k_clusters=None,
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
            detail=f"Customer segmentation retrieval failed: {str(e)}",
        )


@router.post("/{dataset_id}/churn/train", response_model=ChurnOverviewResponse)
async def train_churn(
    dataset_id: str,
    request: Optional[ChurnTrainRequest] = None,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fit or retrain Supervised Customer Churn classifier."""
    model_type = request.model_type if request else "auto"
    inact_days = request.inactivity_threshold_days if request else None
    try:
        return await run_customer_churn_prediction(
            dataset_id=dataset_id,
            organization_id=organization_id,
            model_type=model_type,
            inactivity_threshold_days=inact_days,
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
            detail=f"Customer churn training failed: {str(e)}",
        )


@router.get("/{dataset_id}/churn/overview", response_model=ChurnOverviewResponse)
async def get_churn_overview(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve model performance metrics, risk distribution, and top feature drivers."""
    try:
        return await run_customer_churn_prediction(
            dataset_id=dataset_id,
            organization_id=organization_id,
            model_type="auto",
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
            detail=f"Customer churn overview failed: {str(e)}",
        )


@router.get("/{dataset_id}/churn/customers", response_model=ChurnCustomerListResponse)
async def get_churn_customers(
    dataset_id: str,
    risk_level: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve individual scored customers with risk factors and retention playbooks."""
    try:
        return await get_churn_customers_paginated(
            dataset_id=dataset_id,
            organization_id=organization_id,
            risk_level=risk_level,
            search=search,
            page=page,
            page_size=page_size,
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
            detail=f"Failed retrieving churn customers: {str(e)}",
        )


@router.post("/{dataset_id}/forecast/train", response_model=ForecastResponse)
async def train_forecast(
    dataset_id: str,
    request: Optional[ForecastTrainRequest] = None,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fit time-series model (Holt-Winters / ARIMA / Linear) and project forward revenue horizon."""
    m_type = request.model_type if request else "auto"
    horizon = request.horizon_days if request else 30
    conf = request.confidence_level if request else 0.95
    try:
        return await run_sales_forecasting(
            dataset_id=dataset_id,
            organization_id=organization_id,
            model_type=m_type,
            horizon_days=horizon,
            confidence_level=conf,
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
            detail=f"Sales forecasting failed: {str(e)}",
        )


@router.get("/{dataset_id}/forecast/results", response_model=ForecastResponse)
async def get_forecast_results(
    dataset_id: str,
    horizon_days: Optional[int] = 30,
    confidence_level: Optional[float] = 0.95,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve existing sales forecast or run initial projection."""
    try:
        return await run_sales_forecasting(
            dataset_id=dataset_id,
            organization_id=organization_id,
            model_type="auto",
            horizon_days=horizon_days or 30,
            confidence_level=confidence_level or 0.95,
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
            detail=f"Sales forecast retrieval failed: {str(e)}",
        )


@router.post("/{dataset_id}/anomalies/detect", response_model=AnomalyOverviewResponse)
async def detect_anomalies(
    dataset_id: str,
    request: Optional[AnomalyDetectRequest] = None,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run Isolation Forest and Modified Z-Score to detect fraudulent or anomalous orders."""
    contam = request.contamination if request else 0.02
    sens = request.sensitivity if request else "balanced"
    try:
        return await run_transaction_anomaly_detection(
            dataset_id=dataset_id,
            organization_id=organization_id,
            contamination=contam,
            sensitivity=sens,
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
            detail=f"Anomaly detection failed: {str(e)}",
        )


@router.get("/{dataset_id}/anomalies/list", response_model=AnomalyOverviewResponse)
async def get_anomalies_list(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve existing anomaly scan results or run initial detection."""
    try:
        return await get_or_run_anomalies(
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
            detail=f"Anomaly retrieval failed: {str(e)}",
        )


@router.patch("/{dataset_id}/anomalies/{anomaly_id}/review", response_model=AnomalyItem)
async def review_anomaly(
    dataset_id: str,
    anomaly_id: str,
    request: AnomalyReviewRequest,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update operator review state for a flagged anomaly."""
    try:
        return await review_anomaly_record(
            dataset_id=dataset_id,
            organization_id=organization_id,
            anomaly_id=anomaly_id,
            review_status=request.review_status,
            notes=request.notes,
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
            detail=f"Anomaly review failed: {str(e)}",
        )


@router.post("/{dataset_id}/sentiment/analyze", response_model=SentimentOverviewResponse)
async def analyze_customer_sentiment(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger Natural Language Processing (NLP) sentiment, aspect, and keyword extraction over customer reviews."""
    try:
        return await run_customer_sentiment_analysis(
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
            detail=f"Customer sentiment analysis failed: {str(e)}",
        )


@router.get("/{dataset_id}/sentiment/overview", response_model=SentimentOverviewResponse)
async def get_sentiment_overview(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve existing sentiment intelligence overview or execute initial NLP run."""
    try:
        return await run_customer_sentiment_analysis(
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
            detail=f"Sentiment overview retrieval failed: {str(e)}",
        )





