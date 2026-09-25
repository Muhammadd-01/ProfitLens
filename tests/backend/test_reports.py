"""Unit tests for Phase 17 Multi-Format Report Generation Engine."""

import os
import io
import pytest
import pandas as pd
import numpy as np

from app.schemas.reports import ReportGenerateRequest, ReportMetadataItem, ReportListResponse
from app.services.report_service import (
    generate_executive_pdf_content,
    generate_csv_export_content,
    NumberedCanvas,
)


@pytest.fixture
def sample_dataset_df():
    """Generates synthetic dataset for report compilation."""
    dates = pd.date_range("2026-01-01", periods=60, freq="D")
    return pd.DataFrame({
        "order_id": [f"ORD-{i:04d}" for i in range(60)],
        "order_date": dates,
        "revenue": [50.0 + (i % 7) * 25.0 + (i % 3) * 15.0 for i in range(60)],
        "customer_id": [f"CUST-{(i % 12):03d}" for i in range(60)],
        "category": ["Electronics" if i % 2 == 0 else "Apparel" for i in range(60)],
        "product_id": [f"SKU-{(i % 8):03d}" for i in range(60)],
    })


@pytest.fixture
def sample_col_meta():
    """Generates synthetic downstream metadata across all analytic modules."""
    return {
        "churn_results": {
            "total_customers_evaluated": 250,
            "total_revenue_at_risk": 12500.0,
            "metrics": {"roc_auc": 0.88, "precision": 0.82, "recall": 0.79},
            "risk_distribution": {
                "critical_count": 14,
                "critical_pct": 5.6,
                "high_count": 28,
                "high_pct": 11.2,
                "medium_count": 55,
                "medium_pct": 22.0,
                "low_count": 153,
                "low_pct": 61.2,
            },
        },
        "anomaly_results": {
            "total_orders_scanned": 1200,
            "distribution": {
                "total_anomalies": 12,
                "total_flagged_revenue": 6450.0,
                "critical_count": 3,
                "high_count": 5,
                "medium_count": 4,
                "low_count": 0,
            },
            "top_anomalies": [
                {
                    "order_id": "ORD-999",
                    "order_date": "2026-02-15",
                    "amount": 2500.0,
                    "severity": "critical",
                    "reason": "Amount 8.5x category median",
                },
                {
                    "order_id": "ORD-888",
                    "order_date": "2026-02-14",
                    "amount": 1800.0,
                    "severity": "high",
                    "reason": "Unusual burst velocity",
                },
            ],
        },
        "product_intelligence": {
            "total_products": 45,
            "total_revenue": 89000.0,
            "bcg_distribution": {
                "stars_count": 8,
                "stars_revenue": 45000.0,
                "cash_cows_count": 12,
                "cash_cows_revenue": 30000.0,
                "question_marks_count": 10,
                "question_marks_revenue": 9000.0,
                "dogs_count": 15,
                "dogs_revenue": 5000.0,
            },
        },
        "sentiment_analysis": {
            "distribution": {
                "total_reviews": 320,
                "positive_count": 210,
                "neutral_count": 65,
                "negative_count": 45,
                "net_sentiment_score": 51.56,
                "avg_rating": 4.35,
            },
            "aspects": [
                {
                    "aspect": "Product Quality",
                    "total_mentions": 180,
                    "avg_sentiment_score": 0.45,
                    "sentiment_label": "mostly_positive",
                },
                {
                    "aspect": "Shipping & Delivery",
                    "total_mentions": 75,
                    "avg_sentiment_score": -0.15,
                    "sentiment_label": "mixed",
                },
            ],
        },
    }


def test_generate_pdf_report_content(sample_dataset_df, sample_col_meta):
    """Verifies that PDF compilation executes cleanly and generates valid PDF binary."""
    req = ReportGenerateRequest(
        report_type="executive_summary",
        format="pdf",
        title="ProfitLens Q1 Executive Review",
        include_churn=True,
        include_anomalies=True,
        include_products=True,
        include_sentiment=True,
    )

    pdf_bytes, kpis = generate_executive_pdf_content(
        dataset_name="Retail Sales 2026",
        df=sample_dataset_df,
        col_meta=sample_col_meta,
        req=req,
        date_col="order_date",
        rev_col="revenue",
        order_id_col="order_id",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000  # Non-trivial document size
    assert pdf_bytes.startswith(b"%PDF")  # Valid PDF header

    # Verify extracted KPIs
    assert kpis["total_revenue"] > 0
    assert kpis["total_orders"] == 60
    assert kpis["revenue_at_risk"] == 12500.0
    assert kpis["anomalies_flagged"] == 12
    assert kpis["net_sentiment_score"] == 51.56


def test_generate_csv_report_content(sample_dataset_df, sample_col_meta):
    """Verifies that consolidated financial CSV audit generation produces valid UTF-8 structured data."""
    csv_bytes, kpis = generate_csv_export_content(
        dataset_name="Retail Sales 2026",
        df=sample_dataset_df,
        col_meta=sample_col_meta,
        date_col="order_date",
        rev_col="revenue",
        order_id_col="order_id",
    )

    assert isinstance(csv_bytes, bytes)
    text = csv_bytes.decode("utf-8")
    assert "# ProfitLens Executive Intelligence CSV Export" in text
    assert "--- EXECUTIVE METRICS ---" in text
    assert "--- MONTHLY PERFORMANCE ---" in text
    assert "--- TRANSACTION ANOMALY TRIAGE ---" in text
    assert "ORD-999" in text


def test_numbered_canvas_two_pass():
    """Verifies that NumberedCanvas properly tracks and stamps running footer page counts."""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("First Page", styles["Heading1"]),
        PageBreak(),
        Paragraph("Second Page", styles["Heading1"]),
        PageBreak(),
        Paragraph("Third Page", styles["Heading1"]),
    ]
    doc.build(story, canvasmaker=NumberedCanvas)
    out_bytes = buf.getvalue()
    assert len(out_bytes) > 1000
    assert out_bytes.startswith(b"%PDF")


def test_report_request_validation():
    """Verifies Pydantic schema validation for report configurations."""
    req = ReportGenerateRequest()
    assert req.report_type == "executive_summary"
    assert req.format == "pdf"
    assert req.include_churn is True
    assert req.include_anomalies is True

    # Custom request
    custom = ReportGenerateRequest(
        report_type="risk_assessment",
        format="csv",
        title="Internal Audit",
        include_churn=False,
    )
    assert custom.report_type == "risk_assessment"
    assert custom.format == "csv"
    assert custom.include_churn is False
