"""Reports & Corporate Deliverables API Endpoints."""

from __future__ import annotations

import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_organization_id
from app.models.user import User
from app.schemas.reports import (
    ReportGenerateRequest,
    ReportMetadataItem,
    ReportListResponse,
)
from app.services.report_service import (
    generate_dataset_report,
    list_dataset_reports,
    get_report_file_path,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{dataset_id}/list", response_model=ReportListResponse)
async def list_reports(
    dataset_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve history of all generated PDF and CSV reports for a dataset."""
    try:
        return await list_dataset_reports(
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
            detail=f"Report listing failed: {str(e)}",
        )


@router.post("/{dataset_id}/generate", response_model=ReportMetadataItem)
async def generate_report(
    dataset_id: str,
    request: ReportGenerateRequest,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compile a branded executive PDF or CSV report for a dataset."""
    try:
        return await generate_dataset_report(
            dataset_id=dataset_id,
            organization_id=organization_id,
            request=request,
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
            detail=f"Report generation failed: {str(e)}",
        )


@router.get("/{dataset_id}/download/{report_id}")
async def download_report(
    dataset_id: str,
    report_id: str,
    organization_id: str = Depends(get_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a compiled corporate report file (PDF or CSV)."""
    try:
        file_path, filename, media_type = await get_report_file_path(
            dataset_id=dataset_id,
            report_id=report_id,
            organization_id=organization_id,
            db=db,
        )
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report download failed: {str(e)}",
        )
