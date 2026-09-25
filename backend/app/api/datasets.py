"""Dataset API endpoints for uploading, listing, profiling, and mapping datasets."""

from __future__ import annotations

from typing import List, Dict, Optional
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_organization_id
from app.models.user import User
from app.models.dataset import Dataset
from app.schemas.dataset import (
    DatasetUploadResponse,
    DatasetResponse,
    DatasetListResponse,
    DataQualityReport,
    ColumnMappingResponse,
    SaveColumnMappingRequest,
    SchemaValidationResult,
    CleaningStrategyConfig,
    CleaningSummary,
    FeatureEngineeringResponse,
)
from app.services.dataset_service import (
    process_and_save_upload,
    list_datasets_for_organization,
)
from app.services.profiling_service import profile_dataset
from app.services.mapping_service import (
    get_dataset_mapping_suggestions,
    save_dataset_mappings,
    validate_mapped_schema,
)
from app.services.cleaning_service import clean_dataset
from app.services.feature_service import generate_dataset_features

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("/upload", response_model=DatasetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    organization_id: str = Depends(get_organization_id),
    db: AsyncSession = Depends(get_db),
):
    """Upload a business dataset (CSV or XLSX)."""
    return await process_and_save_upload(
        file=file,
        organization_id=organization_id,
        user_id=str(current_user.id),
        db=db,
    )


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all datasets owned by the user's organization."""
    datasets = await list_datasets_for_organization(
        organization_id=organization_id,
        db=db,
    )
    return DatasetListResponse(datasets=datasets, total=len(datasets))


@router.post("/{dataset_id}/profile", response_model=DataQualityReport)
async def run_profiling(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute automated data profiling and quality scoring on a dataset."""
    try:
        return await profile_dataset(
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
            detail=f"Profiling failed: {str(e)}",
        )


@router.get("/{dataset_id}/profile", response_model=DataQualityReport)
async def get_profiling_report(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the data profiling and quality report for a dataset."""
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == uuid.UUID(dataset_id),
            Dataset.organization_id == uuid.UUID(organization_id),
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    # If already profiled, return cached results
    if dataset.profiling_results and "quality_score" in dataset.profiling_results:
        return DataQualityReport(**dataset.profiling_results)

    # Otherwise, trigger profiling on demand
    try:
        return await profile_dataset(
            dataset_id=dataset_id,
            organization_id=organization_id,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profiling failed: {str(e)}",
        )


@router.get("/{dataset_id}/mappings", response_model=ColumnMappingResponse)
async def get_mappings(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get smart suggested column mappings for a dataset."""
    try:
        return await get_dataset_mapping_suggestions(
            dataset_id=dataset_id,
            organization_id=organization_id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{dataset_id}/mappings", response_model=SchemaValidationResult)
async def save_mappings(
    dataset_id: str,
    request: SaveColumnMappingRequest,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save confirmed column mappings and return module readiness validation."""
    try:
        return await save_dataset_mappings(
            dataset_id=dataset_id,
            organization_id=organization_id,
            mappings=request.mappings,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{dataset_id}/validate", response_model=SchemaValidationResult)
async def validate_dataset_schema(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate current column mappings against downstream ML requirements."""
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == uuid.UUID(dataset_id),
            Dataset.organization_id == uuid.UUID(organization_id),
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    mappings = dataset.column_mappings or {}
    validation = validate_mapped_schema(mappings)
    validation.dataset_id = str(dataset.id)
    return validation


@router.post("/{dataset_id}/clean", response_model=CleaningSummary)
async def run_clean_dataset(
    dataset_id: str,
    config: Optional[CleaningStrategyConfig] = None,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute data cleaning and transformation pipeline on dataset."""
    try:
        return await clean_dataset(
            dataset_id=dataset_id,
            organization_id=organization_id,
            config=config,
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
            detail=f"Cleaning failed: {str(e)}",
        )


@router.get("/{dataset_id}/clean-summary", response_model=CleaningSummary)
async def get_cleaning_summary(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get transformation audit trail and summary for a cleaned dataset."""
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == uuid.UUID(dataset_id),
            Dataset.organization_id == uuid.UUID(organization_id),
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    col_meta = dataset.column_metadata or {}
    summary = col_meta.get("cleaning_summary")
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset has not been cleaned yet",
        )

    return CleaningSummary(**summary)


@router.post("/{dataset_id}/features/generate", response_model=FeatureEngineeringResponse)
async def generate_features(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate model-ready customer RFM and time-series feature tables."""
    try:
        return await generate_dataset_features(
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
            detail=f"Feature generation failed: {str(e)}",
        )


@router.get("/{dataset_id}/features/summary", response_model=FeatureEngineeringResponse)
async def get_features_summary(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get or generate the engineered features catalog and summaries for a dataset."""
    try:
        return await generate_dataset_features(
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
            detail=f"Feature retrieval failed: {str(e)}",
        )
