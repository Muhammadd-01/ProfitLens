"""Unit tests for Automated Executive Insights Engine."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from app.services.insights_service import (
    evaluate_revenue_insights,
    evaluate_churn_insights,
    evaluate_anomaly_insights,
    evaluate_product_insights,
    evaluate_sentiment_insights,
)


def test_evaluate_revenue_insights_expansion():
    """Verify positive insight generated when period-over-period sales expand."""
    start_date = datetime(2023, 1, 1)
    records = []
    # Period 1 (Days 0-14): 10 orders of $50 = $500
    for i in range(15):
        records.append({
            "order_id": f"O-P1-{i}",
            "order_date": start_date + timedelta(days=i),
            "revenue": 50.0,
        })
    # Period 2 (Days 15-29): 15 orders of $150 = $2,250 (+350% growth)
    for i in range(15):
        records.append({
            "order_id": f"O-P2-{i}",
            "order_date": start_date + timedelta(days=15 + i),
            "revenue": 150.0,
        })

    df = pd.DataFrame(records)
    insights = evaluate_revenue_insights({}, df, "order_date", "revenue", "order_id")

    assert len(insights) >= 1
    exp_ins = insights[0]
    assert exp_ins.category == "revenue"
    assert exp_ins.severity == "positive"
    assert "Momentum" in exp_ins.title or "Expansion" in exp_ins.title
    assert len(exp_ins.recommended_action) > 10


def test_evaluate_churn_insights():
    """Verify critical / warning insight generation when high churn risk is present."""
    col_meta = {
        "churn_results": {
            "total_customers_scored": 200,
            "overall_churn_rate_pct": 24.5,
            "risk_distribution": {
                "critical_count": 15,
                "high_count": 25,
                "critical_risk_revenue": 4500.0,
                "high_risk_revenue": 6200.0,
            },
        }
    }

    insights = evaluate_churn_insights(col_meta)
    assert len(insights) == 1
    ins = insights[0]
    assert ins.category == "churn"
    assert ins.severity == "critical"
    assert "10,700" in ins.title or "10700" in ins.title or "Risk" in ins.title
    assert "retention" in ins.recommended_action.lower()


def test_evaluate_anomaly_insights():
    """Verify anomaly warning generated when unreviewed outliers exist."""
    col_meta = {
        "anomaly_results": {
            "distribution": {
                "total_anomalies": 8,
                "critical_count": 2,
                "total_flagged_revenue": 8450.0,
                "reviewed_count": 1,
            }
        }
    }

    insights = evaluate_anomaly_insights(col_meta)
    assert len(insights) == 1
    ins = insights[0]
    assert ins.category == "anomalies"
    assert ins.severity == "critical"
    assert "8,450" in ins.title or "8450" in ins.title or "Anomalies" in ins.title
    assert ins.supporting_data["unreviewed"] == 7


def test_evaluate_product_insights():
    """Verify BCG Star recognition and Dog SKU rationalization alerts."""
    col_meta = {
        "product_intelligence": {
            "distribution": {
                "stars_count": 4,
                "cash_cows_count": 6,
                "dogs_count": 12,
                "total_products": 25,
                "stars_revenue": 34000.0,
                "dogs_revenue": 1200.0,
            }
        }
    }

    insights = evaluate_product_insights(col_meta)
    assert len(insights) >= 2
    cats = [i.category for i in insights]
    assert all(c == "products" for c in cats)

    star_ins = next(i for i in insights if i.id == "prod-stars")
    assert star_ins.severity == "positive"

    dog_ins = next(i for i in insights if i.id == "prod-dogs")
    assert dog_ins.severity == "warning"
    assert "clearance" in dog_ins.recommended_action.lower() or "liquidat" in dog_ins.recommended_action.lower()


def test_evaluate_sentiment_insights():
    """Verify Net Sentiment Score alerts."""
    high_nss_meta = {
        "sentiment_analysis": {
            "net_sentiment_score": 58.2,
            "total_reviews": 400,
            "distribution": {
                "positive_count": 280,
                "negative_count": 47,
            },
        }
    }

    insights = evaluate_sentiment_insights(high_nss_meta)
    assert len(insights) == 1
    assert insights[0].category == "sentiment"
    assert insights[0].severity == "positive"
    assert "58.2%" in insights[0].title
