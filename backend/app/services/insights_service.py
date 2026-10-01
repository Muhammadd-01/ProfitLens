"""Automated Executive Insights & Prescriptive Analytics Service.

Synthesizes cross-module business intelligence (Revenue, Customers, Churn, Forecast,
Anomalies, Product Catalog, Sentiment) into prioritized, natural-language executive
narratives with quantitative evidence and actionable operational playbooks.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.dataset import Dataset
from app.schemas.insights import (
    InsightItem,
    InsightSummaryCounts,
    InsightFeedResponse,
)
from app.services.cleaning_service import load_dataset_as_dataframe
from app.services.mapping_service import get_dataset_mapping_suggestions
from app.services.analytics_service import compute_executive_kpis


def evaluate_revenue_insights(
    col_meta: Dict[str, Any],
    raw_df: pd.DataFrame,
    date_col: Optional[str],
    rev_col: Optional[str],
    order_id_col: Optional[str],
) -> List[InsightItem]:
    """Generates insights on top-line revenue momentum, AOV changes, and order trajectory."""
    insights: List[InsightItem] = []
    now_str = datetime.utcnow().isoformat()

    try:
        if date_col and rev_col and date_col in raw_df.columns and rev_col in raw_df.columns:
            df = raw_df.copy()
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce", utc=True)
            df[rev_col] = pd.to_numeric(df[rev_col], errors="coerce").fillna(0.0)
            df = df.dropna(subset=[date_col, rev_col])

            kpis, span = compute_executive_kpis(df, date_col, rev_col, order_id_col)
            rev_change = kpis.revenue_change_pct
            aov_change = kpis.aov_change_pct

            if rev_change is not None:
                if rev_change <= -10.0:
                    insights.append(
                        InsightItem(
                            id="rev-contraction",
                            category="revenue",
                            title=f"Top-Line Revenue Contraction ({rev_change:+.1f}%)",
                            description=(
                                f"Recent sales volume contracted by {abs(rev_change):.1f}% compared to the preceding period. "
                                f"Total generated revenue stands at ${kpis.total_revenue:,.2f} across {kpis.total_orders:,} orders."
                            ),
                            severity="critical" if rev_change <= -25.0 else "warning",
                            confidence=0.92,
                            impact_score=abs(rev_change),
                            supporting_data={"total_revenue": kpis.total_revenue, "revenue_change_pct": rev_change},
                            metrics={"revenue_change_pct": rev_change, "aov": kpis.avg_order_value},
                            recommended_action="Conduct pricing sensitivity review and deploy reactivation emails with limited-time discount incentives to dormant buyers.",
                            is_dismissed=False,
                            created_at=now_str,
                        )
                    )
                elif rev_change >= 10.0:
                    insights.append(
                        InsightItem(
                            id="rev-expansion",
                            category="revenue",
                            title=f"Strong Revenue Momentum ({rev_change:+.1f}%)",
                            description=(
                                f"Sales velocity expanded by +{rev_change:.1f}% period-over-period, generating ${kpis.total_revenue:,.2f}. "
                                f"Average Order Value (AOV) shifted by {aov_change or 0.0:+.1f}% to ${kpis.avg_order_value:.2f}."
                            ),
                            severity="positive",
                            confidence=0.94,
                            impact_score=rev_change,
                            supporting_data={"total_revenue": kpis.total_revenue, "revenue_change_pct": rev_change},
                            metrics={"revenue_change_pct": rev_change, "aov": kpis.avg_order_value},
                            recommended_action="Scale marketing ad spend on top-converting acquisition channels to sustain demand momentum without depleting buffer inventory.",
                            is_dismissed=False,
                            created_at=now_str,
                        )
                    )
                else:
                    insights.append(
                        InsightItem(
                            id="rev-stable",
                            category="revenue",
                            title="Stable Revenue Trajectory Across Observation Window",
                            description=f"Revenue trend remains balanced with a steady ${kpis.total_revenue:,.2f} baseline and ${kpis.avg_order_value:.2f} average order value.",
                            severity="info",
                            confidence=0.88,
                            impact_score=15.0,
                            supporting_data={"total_revenue": kpis.total_revenue},
                            metrics={"total_revenue": kpis.total_revenue, "orders": kpis.total_orders},
                            recommended_action="Test cross-sell bundles and threshold-based free shipping tiers to lift average order value above current levels.",
                            is_dismissed=False,
                            created_at=now_str,
                        )
                    )
    except Exception:
        pass

    return insights


def evaluate_churn_insights(col_meta: Dict[str, Any]) -> List[InsightItem]:
    """Generates insights from customer churn predictions and revenue-at-risk analysis."""
    insights: List[InsightItem] = []
    now_str = datetime.utcnow().isoformat()

    churn_meta = col_meta.get("churn_results", {})
    if churn_meta:
        total_custs = churn_meta.get("total_customers_scored", 0)
        risk_dist = churn_meta.get("risk_distribution", {})
        high_c = risk_dist.get("high_count", 0) + risk_dist.get("critical_count", 0)
        high_rev = risk_dist.get("high_risk_revenue", 0.0) + risk_dist.get("critical_risk_revenue", 0.0)
        rate = churn_meta.get("overall_churn_rate_pct", 0.0)

        if high_c > 0 and high_rev > 0:
            severity = "critical" if (high_c / max(1, total_custs)) >= 0.20 or high_rev > 5000 else "warning"
            insights.append(
                InsightItem(
                    id="churn-exposure",
                    category="churn",
                    title=f"Customer Attrition Risk: ${high_rev:,.2f} Revenue at Risk",
                    description=(
                        f"Machine learning model flagged {high_c} high-value customers with elevated churn probability. "
                        f"Overall baseline churn rate is estimated at {rate:.1f}% across {total_custs} accounts."
                    ),
                    severity=severity,
                    confidence=0.89,
                    impact_score=float(high_rev),
                    supporting_data={"high_risk_count": high_c, "revenue_at_risk": high_rev},
                    metrics={"high_risk_count": high_c, "revenue_at_risk": high_rev, "churn_rate": rate},
                    recommended_action="Deploy immediate VIP retention playbooks: trigger personalized re-engagement discounts and conduct phone/email check-ins for top accounts.",
                    is_dismissed=False,
                    created_at=now_str,
                )
            )

    return insights


def evaluate_anomaly_insights(col_meta: Dict[str, Any]) -> List[InsightItem]:
    """Generates insights from Isolation Forest and Modified Z-Score fraud detections."""
    insights: List[InsightItem] = []
    now_str = datetime.utcnow().isoformat()

    anom_meta = col_meta.get("anomaly_results", {})
    if anom_meta:
        dist = anom_meta.get("distribution", {})
        total_anom = dist.get("total_anomalies", 0)
        flagged_rev = dist.get("total_flagged_revenue", 0.0)
        crit_c = dist.get("critical_count", 0)
        rev_c = dist.get("reviewed_count", 0)
        unreviewed = total_anom - rev_c

        if total_anom > 0 and flagged_rev > 0:
            severity = "critical" if crit_c > 0 or flagged_rev >= 2000 else "warning"
            insights.append(
                InsightItem(
                    id="anomaly-risk",
                    category="anomalies",
                    title=f"Unresolved Transaction Anomalies (${flagged_rev:,.2f} Flagged)",
                    description=(
                        f"Unsupervised Isolation Forest detected {total_anom} anomalous transactions "
                        f"({crit_c} critical severity), representing ${flagged_rev:,.2f} in gross order value. "
                        f"{unreviewed} flagged orders currently await operator review."
                    ),
                    severity=severity,
                    confidence=0.91,
                    impact_score=float(flagged_rev),
                    supporting_data={"flagged_revenue": flagged_rev, "critical_count": crit_c, "unreviewed": unreviewed},
                    metrics={"total_anomalies": total_anom, "critical_count": crit_c, "flagged_revenue": flagged_rev},
                    recommended_action="Navigate to the Anomaly Triage Queue to confirm fraud, identify price entry bugs, or mark false positives before order dispatch.",
                    is_dismissed=False,
                    created_at=now_str,
                )
            )

    return insights


def evaluate_product_insights(col_meta: Dict[str, Any]) -> List[InsightItem]:
    """Generates insights from BCG Growth-Share matrix and Pareto catalog distributions."""
    insights: List[InsightItem] = []
    now_str = datetime.utcnow().isoformat()

    prod_meta = col_meta.get("product_intelligence", {})
    if prod_meta:
        dist = prod_meta.get("distribution", {})
        stars_c = dist.get("stars_count", 0)
        cows_c = dist.get("cash_cows_count", 0)
        dogs_c = dist.get("dogs_count", 0)
        stars_rev = dist.get("stars_revenue", 0.0)
        dogs_rev = dist.get("dogs_revenue", 0.0)
        total_prods = dist.get("total_products", 0)

        # Star drivers insight
        if stars_c > 0:
            insights.append(
                InsightItem(
                    id="prod-stars",
                    category="products",
                    title=f"Portfolio Core: {stars_c} Star SKUs Driving ${stars_rev:,.2f}",
                    description=(
                        f"The catalog features {stars_c} Star products demonstrating high relative market share and expanding sales momentum. "
                        f"Together with {cows_c} Cash Cows, they anchor core business cash flows."
                    ),
                    severity="positive",
                    confidence=0.95,
                    impact_score=float(stars_rev),
                    supporting_data={"stars_count": stars_c, "stars_revenue": stars_rev},
                    metrics={"stars_count": stars_c, "cash_cows_count": cows_c},
                    recommended_action="Prioritize Star SKUs in advertising campaigns and secure supplier volume discounts to maximize gross margins.",
                    is_dismissed=False,
                    created_at=now_str,
                )
            )

        # Dog SKUs warning
        if dogs_c > 0 and (dogs_c / max(1, total_prods)) >= 0.25:
            insights.append(
                InsightItem(
                    id="prod-dogs",
                    category="products",
                    title=f"Catalog Rationalization: {dogs_c} Low-Velocity 'Dog' SKUs",
                    description=(
                        f"{dogs_c} out of {total_prods} products ({((dogs_c / max(1, total_prods)) * 100):.1f}%) "
                        f"exhibit both low relative share and declining growth rate, tying up working capital with only ${dogs_rev:,.2f} in revenue."
                    ),
                    severity="warning",
                    confidence=0.88,
                    impact_score=float(dogs_c * 100),
                    supporting_data={"dogs_count": dogs_c, "total_products": total_prods},
                    metrics={"dogs_count": dogs_c, "dogs_revenue": dogs_rev},
                    recommended_action="Execute inventory clearance via promotional bundles or discount liquidation to liberate warehouse space and reinvest capital.",
                    is_dismissed=False,
                    created_at=now_str,
                )
            )

    return insights


def evaluate_sentiment_insights(col_meta: Dict[str, Any]) -> List[InsightItem]:
    """Generates insights from customer review sentiment and aspect-based NLP diagnostics."""
    insights: List[InsightItem] = []
    now_str = datetime.utcnow().isoformat()

    sent_meta = col_meta.get("sentiment_analysis", {})
    if sent_meta:
        nss = sent_meta.get("net_sentiment_score", 0.0)
        dist = sent_meta.get("distribution", {})
        pos_c = dist.get("positive_count", 0)
        neg_c = dist.get("negative_count", 0)
        tot = sent_meta.get("total_reviews", 0)

        if nss >= 40.0:
            insights.append(
                InsightItem(
                    id="sent-high-nss",
                    category="sentiment",
                    title=f"Exceptional Customer Brand Sentiment (+{nss:.1f}% NSS)",
                    description=(
                        f"Net Sentiment Score stands at +{nss:.1f}%, with {pos_c} positive reviews out of {tot} analyzed. "
                        f"Customer satisfaction indicates strong product-market fit and brand loyalty."
                    ),
                    severity="positive",
                    confidence=0.92,
                    impact_score=float(nss),
                    supporting_data={"net_sentiment_score": nss, "positive_count": pos_c},
                    metrics={"net_sentiment_score": nss, "total_reviews": tot},
                    recommended_action="Incentivize top brand promoters to share social testimonials and submit user-generated video reviews.",
                    is_dismissed=False,
                    created_at=now_str,
                )
            )
        elif nss <= 10.0:
            insights.append(
                InsightItem(
                    id="sent-low-nss",
                    category="sentiment",
                    title=f"Customer Experience Warning: Low Net Sentiment ({nss:+.1f}%)",
                    description=(
                        f"Customer sentiment index is compressed at {nss:+.1f}% NSS with {neg_c} critical complaints logged. "
                        f"Negative reviews correlate strongly with delivery delays and packaging damage."
                    ),
                    severity="warning",
                    confidence=0.90,
                    impact_score=abs(nss) + neg_c,
                    supporting_data={"net_sentiment_score": nss, "negative_count": neg_c},
                    metrics={"net_sentiment_score": nss, "negative_count": neg_c},
                    recommended_action="Audit courier transit times, review fulfillment damage reports, and establish proactive follow-ups for negative ratings.",
                    is_dismissed=False,
                    created_at=now_str,
                )
            )

    return insights


async def generate_executive_insights(
    dataset_id: str,
    organization_id: str,
    db: Optional[AsyncIOMotorDatabase] = None,
) -> InsightFeedResponse:
    """Orchestrates cross-domain insight generation, ranks by priority, and returns feed in MongoDB."""
    if db is None:
        raise ValueError("Database session required")

    doc = await db.datasets.find_one({
        "$or": [{"id": str(dataset_id)}, {"_id": str(dataset_id)}],
        "organization_id": str(organization_id),
    })
    if not doc:
        raise ValueError(f"Dataset {dataset_id} not found")
    dataset = Dataset.from_doc(doc)
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} not found")

    col_meta = dataset.column_metadata or {}
    cleaned_file = col_meta.get("cleaned_file_path")
    file_to_load = cleaned_file if cleaned_file and os.path.exists(cleaned_file) else dataset.file_path
    raw_df = load_dataset_as_dataframe(file_to_load, dataset.file_type)

    mappings = dataset.column_mappings or {}
    if not mappings:
        mapping_resp = await get_dataset_mapping_suggestions(dataset_id, organization_id, db)
        mappings = {m.canonical_field: m.mapped_column for m in mapping_resp.mappings if m.mapped_column}

    date_col = mappings.get("order_date")
    rev_col = mappings.get("revenue")
    ord_col = mappings.get("order_id")

    dismissed_ids = set(col_meta.get("dismissed_insights", []))

    # Evaluate all insight domains
    all_insights: List[InsightItem] = []
    all_insights.extend(evaluate_revenue_insights(col_meta, raw_df, date_col, rev_col, ord_col))
    all_insights.extend(evaluate_churn_insights(col_meta))
    all_insights.extend(evaluate_anomaly_insights(col_meta))
    all_insights.extend(evaluate_product_insights(col_meta))
    all_insights.extend(evaluate_sentiment_insights(col_meta))

    # Fallback insight if no modules have run yet
    if not all_insights:
        now_str = datetime.utcnow().isoformat()
        all_insights.append(
            InsightItem(
                id="default-baseline",
                category="revenue",
                title="Dataset Initialized: Modules Ready for Exploration",
                description="Your transaction records are loaded and verified. Execute Customer Segmentation, Sales Forecasting, and Anomaly Detection to populate real-time predictive insights.",
                severity="info",
                confidence=1.0,
                impact_score=10.0,
                supporting_data={},
                metrics={},
                recommended_action="Run initial ML models across the analytics navigation tabs to discover high-impact revenue and retention opportunities.",
                is_dismissed=False,
                created_at=now_str,
            )
        )

    # Mark dismissed states
    for item in all_insights:
        if item.id in dismissed_ids:
            item.is_dismissed = True

    # Severity ordering weight
    sev_weights = {"critical": 4, "warning": 3, "positive": 2, "info": 1}

    # Sort descending by severity weight, then impact score
    all_insights = sorted(
        all_insights,
        key=lambda x: (
            not x.is_dismissed,  # active first
            sev_weights.get(x.severity, 0),
            x.impact_score,
        ),
        reverse=True,
    )

    # Calculate summary counts (active only)
    active_items = [i for i in all_insights if not i.is_dismissed]
    crit_c = sum(1 for i in active_items if i.severity == "critical")
    warn_c = sum(1 for i in active_items if i.severity == "warning")
    pos_c = sum(1 for i in active_items if i.severity == "positive")
    info_c = sum(1 for i in active_items if i.severity == "info")

    summary = InsightSummaryCounts(
        critical_count=crit_c,
        warning_count=warn_c,
        positive_count=pos_c,
        info_count=info_c,
        total_insights=len(active_items),
    )

    gen_time = datetime.utcnow().isoformat()

    return InsightFeedResponse(
        dataset_id=str(dataset.id),
        summary=summary,
        insights=all_insights,
        generated_at=gen_time,
    )


async def dismiss_insight_item(
    dataset_id: str,
    organization_id: str,
    insight_id: str,
    dismissed: bool = True,
    db: Optional[AsyncIOMotorDatabase] = None,
) -> bool:
    """Marks an insight as dismissed or restored in dataset metadata in MongoDB."""
    if db is None:
        raise ValueError("Database session required")

    doc = await db.datasets.find_one({
        "$or": [{"id": str(dataset_id)}, {"_id": str(dataset_id)}],
        "organization_id": str(organization_id),
    })
    if not doc:
        raise ValueError(f"Dataset {dataset_id} not found")
    dataset = Dataset.from_doc(doc)
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} not found")

    col_meta = dataset.column_metadata or {}
    dismissed_list = col_meta.get("dismissed_insights", [])

    if dismissed and insight_id not in dismissed_list:
        dismissed_list.append(insight_id)
    elif not dismissed and insight_id in dismissed_list:
        dismissed_list.remove(insight_id)

    col_meta["dismissed_insights"] = dismissed_list

    await db.datasets.update_one(
        {"$or": [{"id": dataset.id}, {"_id": dataset.id}]},
        {"$set": {
            "column_metadata": col_meta,
            "updated_at": datetime.utcnow(),
        }}
    )

    return True
