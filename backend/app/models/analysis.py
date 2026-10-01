"""Analysis models for ProfitLens (MongoDB Edition).

Includes AnalysisRun, Prediction, Anomaly, Insight, and Report.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class AnalysisRun:
    """A single execution of the analysis pipeline."""

    def __init__(
        self,
        id: Optional[str] = None,
        organization_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        triggered_by: Optional[str] = None,
        analysis_type: str = "",
        status: str = "pending",
        progress_percent: Optional[int] = 0,
        current_step: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        results: Optional[Dict[str, Any]] = None,
        model_metrics: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        **kwargs: Any,
    ):
        self.id = str(id or uuid.uuid4())
        self.organization_id = str(organization_id) if organization_id else ""
        self.dataset_id = str(dataset_id) if dataset_id else ""
        self.triggered_by = str(triggered_by) if triggered_by else ""
        self.analysis_type = analysis_type
        self.status = status
        self.progress_percent = progress_percent or 0
        self.current_step = current_step
        self.parameters = parameters or {}
        self.results = results or {}
        self.model_metrics = model_metrics or {}
        self.error_message = error_message
        self.started_at = started_at
        self.completed_at = completed_at

    def to_doc(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        return {
            "_id": self.id,
            "id": self.id,
            "organization_id": self.organization_id,
            "dataset_id": self.dataset_id,
            "triggered_by": self.triggered_by,
            "analysis_type": self.analysis_type,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "parameters": self.parameters,
            "results": self.results,
            "model_metrics": self.model_metrics,
            "error_message": self.error_message,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional[AnalysisRun]:
        if not doc:
            return None
        return cls(
            id=str(doc.get("id") or doc.get("_id")),
            organization_id=str(doc.get("organization_id", "")),
            dataset_id=str(doc.get("dataset_id", "")),
            triggered_by=str(doc.get("triggered_by", "")),
            analysis_type=doc.get("analysis_type", ""),
            status=doc.get("status", "pending"),
            progress_percent=doc.get("progress_percent", 0),
            current_step=doc.get("current_step"),
            parameters=doc.get("parameters") or {},
            results=doc.get("results") or {},
            model_metrics=doc.get("model_metrics") or {},
            error_message=doc.get("error_message"),
            started_at=doc.get("started_at"),
            completed_at=doc.get("completed_at"),
        )


class Prediction:
    """An individual ML prediction."""

    def __init__(
        self,
        id: Optional[str] = None,
        organization_id: Optional[str] = None,
        analysis_run_id: Optional[str] = None,
        prediction_type: str = "",
        entity_type: str = "",
        entity_id: Optional[str] = None,
        predicted_value: Optional[float] = None,
        confidence: Optional[float] = None,
        features_used: Optional[Dict[str, Any]] = None,
        explanation: Optional[Dict[str, Any]] = None,
        prediction_date: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        **kwargs: Any,
    ):
        self.id = str(id or uuid.uuid4())
        self.organization_id = str(organization_id) if organization_id else ""
        self.analysis_run_id = str(analysis_run_id) if analysis_run_id else ""
        self.prediction_type = prediction_type
        self.entity_type = entity_type
        self.entity_id = str(entity_id) if entity_id else None
        self.predicted_value = predicted_value
        self.confidence = confidence
        self.features_used = features_used or {}
        self.explanation = explanation or {}
        self.prediction_date = prediction_date
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_doc(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        return {
            "_id": self.id,
            "id": self.id,
            "organization_id": self.organization_id,
            "analysis_run_id": self.analysis_run_id,
            "prediction_type": self.prediction_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "predicted_value": self.predicted_value,
            "confidence": self.confidence,
            "features_used": self.features_used,
            "explanation": self.explanation,
            "prediction_date": self.prediction_date,
            "created_at": self.created_at,
        }

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional[Prediction]:
        if not doc:
            return None
        return cls(
            id=str(doc.get("id") or doc.get("_id")),
            organization_id=str(doc.get("organization_id", "")),
            analysis_run_id=str(doc.get("analysis_run_id", "")),
            prediction_type=doc.get("prediction_type", ""),
            entity_type=doc.get("entity_type", ""),
            entity_id=str(doc.get("entity_id")) if doc.get("entity_id") else None,
            predicted_value=doc.get("predicted_value"),
            confidence=doc.get("confidence"),
            features_used=doc.get("features_used") or {},
            explanation=doc.get("explanation") or {},
            prediction_date=doc.get("prediction_date"),
            created_at=doc.get("created_at"),
        )


class Anomaly:
    """A detected anomaly in transaction data."""

    def __init__(
        self,
        id: Optional[str] = None,
        organization_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        analysis_run_id: Optional[str] = None,
        order_id: Optional[str] = None,
        anomaly_score: Optional[float] = None,
        severity: str = "medium",
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        is_reviewed: bool = False,
        detected_at: Optional[datetime] = None,
        **kwargs: Any,
    ):
        self.id = str(id or uuid.uuid4())
        self.organization_id = str(organization_id) if organization_id else ""
        self.dataset_id = str(dataset_id) if dataset_id else ""
        self.analysis_run_id = str(analysis_run_id) if analysis_run_id else ""
        self.order_id = str(order_id) if order_id else None
        self.anomaly_score = anomaly_score
        self.severity = severity
        self.reason = reason
        self.details = details or {}
        self.is_reviewed = is_reviewed
        self.detected_at = detected_at or datetime.now(timezone.utc)

    def to_doc(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        return {
            "_id": self.id,
            "id": self.id,
            "organization_id": self.organization_id,
            "dataset_id": self.dataset_id,
            "analysis_run_id": self.analysis_run_id,
            "order_id": self.order_id,
            "anomaly_score": self.anomaly_score,
            "severity": self.severity,
            "reason": self.reason,
            "details": self.details,
            "is_reviewed": self.is_reviewed,
            "detected_at": self.detected_at,
        }

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional[Anomaly]:
        if not doc:
            return None
        return cls(
            id=str(doc.get("id") or doc.get("_id")),
            organization_id=str(doc.get("organization_id", "")),
            dataset_id=str(doc.get("dataset_id", "")),
            analysis_run_id=str(doc.get("analysis_run_id", "")),
            order_id=str(doc.get("order_id")) if doc.get("order_id") else None,
            anomaly_score=doc.get("anomaly_score"),
            severity=doc.get("severity", "medium"),
            reason=doc.get("reason"),
            details=doc.get("details") or {},
            is_reviewed=doc.get("is_reviewed", False),
            detected_at=doc.get("detected_at"),
        )


class Insight:
    """A generated business insight with supporting data."""

    def __init__(
        self,
        id: Optional[str] = None,
        organization_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        analysis_run_id: Optional[str] = None,
        category: str = "general",
        title: str = "",
        description: str = "",
        severity: Optional[str] = "info",
        confidence: Optional[float] = 1.0,
        supporting_data: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        **kwargs: Any,
    ):
        self.id = str(id or uuid.uuid4())
        self.organization_id = str(organization_id) if organization_id else ""
        self.dataset_id = str(dataset_id) if dataset_id else ""
        self.analysis_run_id = str(analysis_run_id) if analysis_run_id else ""
        self.category = category
        self.title = title
        self.description = description
        self.severity = severity
        self.confidence = confidence
        self.supporting_data = supporting_data or {}
        self.metrics = metrics or {}
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_doc(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        return {
            "_id": self.id,
            "id": self.id,
            "organization_id": self.organization_id,
            "dataset_id": self.dataset_id,
            "analysis_run_id": self.analysis_run_id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "confidence": self.confidence,
            "supporting_data": self.supporting_data,
            "metrics": self.metrics,
            "created_at": self.created_at,
        }

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional[Insight]:
        if not doc:
            return None
        return cls(
            id=str(doc.get("id") or doc.get("_id")),
            organization_id=str(doc.get("organization_id", "")),
            dataset_id=str(doc.get("dataset_id", "")),
            analysis_run_id=str(doc.get("analysis_run_id", "")),
            category=doc.get("category", "general"),
            title=doc.get("title", ""),
            description=doc.get("description", ""),
            severity=doc.get("severity", "info"),
            confidence=doc.get("confidence", 1.0),
            supporting_data=doc.get("supporting_data") or {},
            metrics=doc.get("metrics") or {},
            created_at=doc.get("created_at"),
        )


class Report:
    """A generated business analytics report."""

    def __init__(
        self,
        id: Optional[str] = None,
        organization_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        analysis_run_id: Optional[str] = None,
        generated_by: Optional[str] = None,
        title: str = "",
        report_type: str = "executive_summary",
        sections: Optional[Dict[str, Any]] = None,
        file_path: Optional[str] = None,
        format: Optional[str] = "pdf",
        created_at: Optional[datetime] = None,
        **kwargs: Any,
    ):
        self.id = str(id or uuid.uuid4())
        self.organization_id = str(organization_id) if organization_id else ""
        self.dataset_id = str(dataset_id) if dataset_id else ""
        self.analysis_run_id = str(analysis_run_id) if analysis_run_id else None
        self.generated_by = str(generated_by) if generated_by else ""
        self.title = title
        self.report_type = report_type
        self.sections = sections or {}
        self.file_path = file_path
        self.format = format
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_doc(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        return {
            "_id": self.id,
            "id": self.id,
            "organization_id": self.organization_id,
            "dataset_id": self.dataset_id,
            "analysis_run_id": self.analysis_run_id,
            "generated_by": self.generated_by,
            "title": self.title,
            "report_type": self.report_type,
            "sections": self.sections,
            "file_path": self.file_path,
            "format": self.format,
            "created_at": self.created_at,
        }

    @classmethod
    def from_doc(cls, doc: Optional[Dict[str, Any]]) -> Optional[Report]:
        if not doc:
            return None
        return cls(
            id=str(doc.get("id") or doc.get("_id")),
            organization_id=str(doc.get("organization_id", "")),
            dataset_id=str(doc.get("dataset_id", "")),
            analysis_run_id=str(doc.get("analysis_run_id")) if doc.get("analysis_run_id") else None,
            generated_by=str(doc.get("generated_by", "")),
            title=doc.get("title", ""),
            report_type=doc.get("report_type", "executive_summary"),
            sections=doc.get("sections") or {},
            file_path=doc.get("file_path"),
            format=doc.get("format", "pdf"),
            created_at=doc.get("created_at"),
        )
