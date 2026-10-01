"""Dataset model — represents an uploaded business data file (MongoDB Edition)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class Dataset:
    """An uploaded business dataset and its processing state."""

    def __init__(
        self,
        id: Optional[str] = None,
        organization_id: Optional[str] = None,
        uploaded_by: Optional[str] = None,
        name: str = "",
        file_path: str = "",
        file_type: str = "csv",
        file_size_bytes: Optional[int] = None,
        row_count: Optional[int] = None,
        column_count: Optional[int] = None,
        data_quality_score: Optional[float] = None,
        column_mappings: Optional[Dict[str, Any]] = None,
        column_metadata: Optional[Dict[str, Any]] = None,
        profiling_results: Optional[Dict[str, Any]] = None,
        status: str = "uploaded",
        error_message: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs: Any,
    ):
        self.id = str(id or uuid.uuid4())
        self.organization_id = str(organization_id) if organization_id else ""
        self.uploaded_by = str(uploaded_by) if uploaded_by else ""
        self.name = name
        self.file_path = file_path
        self.file_type = file_type
        self.file_size_bytes = file_size_bytes
        self.row_count = row_count
        self.column_count = column_count
        self.data_quality_score = data_quality_score
        self.column_mappings = column_mappings or {}
        self.column_metadata = column_metadata or {}
        self.profiling_results = profiling_results or {}
        self.status = status
        self.error_message = error_message
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_doc(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        return {
            "_id": self.id,
            "id": self.id,
            "organization_id": self.organization_id,
            "uploaded_by": self.uploaded_by,
            "name": self.name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size_bytes": self.file_size_bytes,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "data_quality_score": self.data_quality_score,
            "column_mappings": self.column_mappings,
            "column_metadata": self.column_metadata,
            "profiling_results": self.profiling_results,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional[Dataset]:
        if not doc:
            return None
        return cls(
            id=str(doc.get("id") or doc.get("_id")),
            organization_id=str(doc.get("organization_id", "")),
            uploaded_by=str(doc.get("uploaded_by", "")),
            name=doc.get("name", ""),
            file_path=doc.get("file_path", ""),
            file_type=doc.get("file_type", "csv"),
            file_size_bytes=doc.get("file_size_bytes"),
            row_count=doc.get("row_count"),
            column_count=doc.get("column_count"),
            data_quality_score=doc.get("data_quality_score"),
            column_mappings=doc.get("column_mappings") or {},
            column_metadata=doc.get("column_metadata") or {},
            profiling_results=doc.get("profiling_results") or {},
            status=doc.get("status", "uploaded"),
            error_message=doc.get("error_message"),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )
