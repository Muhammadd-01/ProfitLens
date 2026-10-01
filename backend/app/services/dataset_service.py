"""Dataset service — handles file ingestion, validation, and dataset records (MongoDB Edition)."""

from __future__ import annotations

import os
import uuid
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetUploadResponse, DatasetResponse
from app.utils.file_processing import inspect_csv_file, inspect_excel_file

settings = get_settings()


async def process_and_save_upload(
    file: UploadFile,
    organization_id: str,
    user_id: str,
    db: AsyncIOMotorDatabase,
) -> DatasetUploadResponse:
    """Stream an uploaded file to disk in 64KB chunks and perform initial inspection."""
    filename = file.filename or "uploaded_data.csv"
    ext = filename.split(".")[-1].lower()

    if ext not in ["csv", "xlsx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a CSV or XLSX file.",
        )

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    dataset_id = str(uuid.uuid4())
    storage_filename = f"{dataset_id}.{ext}"
    target_path = os.path.join(settings.UPLOAD_DIR, storage_filename)

    # 1. Stream file to disk in 64KB chunks while tracking total size
    total_bytes = 0
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    try:
        with open(target_path, "wb") as dst:
            while True:
                chunk = await file.read(65536)  # 64 KB chunk
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    dst.close()
                    if os.path.exists(target_path):
                        os.remove(target_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                    )
                dst.write(chunk)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if os.path.exists(target_path):
            os.remove(target_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write uploaded file: {str(e)}",
        )

    if total_bytes == 0:
        if os.path.exists(target_path):
            os.remove(target_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is completely empty.",
        )

    # 2. Inspect structure & headers
    encoding: Optional[str] = None
    delimiter: Optional[str] = None

    try:
        if ext == "csv":
            row_count, columns, encoding, delimiter = inspect_csv_file(target_path)
        else:
            row_count, columns = inspect_excel_file(target_path)
            encoding = "utf-8"
            delimiter = None
    except Exception as e:
        if os.path.exists(target_path):
            os.remove(target_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse file structure: {str(e)}",
        )

    if not columns:
        if os.path.exists(target_path):
            os.remove(target_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File contains no readable column headers.",
        )

    # 3. Create Dataset record in MongoDB
    dataset = Dataset(
        id=dataset_id,
        organization_id=organization_id,
        uploaded_by=user_id,
        name=filename,
        file_path=target_path,
        file_type=ext,
        file_size_bytes=total_bytes,
        row_count=row_count,
        column_count=len(columns),
        status="uploaded",
        column_metadata={"columns": columns},
        profiling_results={
            "initial_inspection": {
                "encoding": encoding,
                "delimiter": delimiter,
                "row_count": row_count,
                "column_count": len(columns),
            }
        },
    )
    await db.datasets.insert_one(dataset.to_doc())

    return DatasetUploadResponse(
        id=str(dataset.id),
        name=dataset.name,
        file_type=dataset.file_type,
        file_size_bytes=total_bytes,
        row_count=row_count,
        column_count=len(columns),
        columns=columns,
        detected_encoding=encoding,
        detected_delimiter=delimiter,
        status=dataset.status,
        created_at=dataset.created_at.isoformat() if dataset.created_at else "",
    )


async def list_datasets_for_organization(
    organization_id: str,
    db: AsyncIOMotorDatabase,
) -> List[DatasetResponse]:
    """List all datasets belonging to the organization in MongoDB."""
    cursor = db.datasets.find({"organization_id": str(organization_id)}).sort("created_at", -1)
    datasets: List[Dataset] = []
    async for doc in cursor:
        d = Dataset.from_doc(doc)
        if d:
            datasets.append(d)

    return [
        DatasetResponse(
            id=str(d.id),
            organization_id=str(d.organization_id),
            uploaded_by=str(d.uploaded_by),
            name=d.name,
            file_type=d.file_type,
            file_size_bytes=d.file_size_bytes,
            row_count=d.row_count,
            column_count=d.column_count,
            data_quality_score=d.data_quality_score,
            column_mappings=d.column_mappings,
            column_metadata=d.column_metadata,
            profiling_results=d.profiling_results,
            status=d.status,
            error_message=d.error_message,
            created_at=d.created_at.isoformat() if d.created_at else "",
            updated_at=d.updated_at.isoformat() if d.updated_at else "",
        )
        for d in datasets
    ]
