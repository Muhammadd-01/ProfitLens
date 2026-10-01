"""Multi-Format Corporate Report Generation Service.

Compiles branded, publication-ready executive intelligence PDF reports and consolidated
financial CSV audit exports using ReportLab Flowables, structured tables, and dynamic styling.
"""

from __future__ import annotations

import io
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from motor.motor_asyncio import AsyncIOMotorDatabase

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

from app.models.dataset import Dataset
from app.schemas.reports import (
    ReportGenerateRequest,
    ReportMetadataItem,
    ReportListResponse,
)
from app.services.cleaning_service import load_dataset_as_dataframe
from app.services.mapping_service import get_dataset_mapping_suggestions
from app.services.analytics_service import compute_executive_kpis, compute_revenue_timeseries
from app.config import get_settings

settings = get_settings()

REPORTS_DIR = os.path.join("data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and render total page count and corporate headers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(36, 756, "ProfitLens Decision Intelligence | Executive Audit Report")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(36, 750, 576, 750)

        # Running footer (all pages)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 45, 576, 45)
        self.drawString(36, 32, "CONFIDENTIAL — STRICTLY FOR INTERNAL MANAGEMENT REVIEW")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(576, 32, page_str)
        self.restoreState()


def build_pdf_styles():
    """Builds a cohesive palette and typography scale for corporate PDF generation."""
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0F172A"),
        alignment=0,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
        spaceAfter=8,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#FFFFFF"),
        alignment=1,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B"),
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell_style,
        fontName="Helvetica-Bold",
    )

    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        alignment=1,
    )

    callout_style = ParagraphStyle(
        "CalloutText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0F172A"),
    )

    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "h1": h1_style,
        "body": body_style,
        "th": table_header_style,
        "td": table_cell_style,
        "td_bold": table_cell_bold,
        "badge": badge_style,
        "callout": callout_style,
    }


def generate_executive_pdf_content(
    dataset_name: str,
    df: pd.DataFrame,
    col_meta: Dict[str, Any],
    req: ReportGenerateRequest,
    date_col: Optional[str],
    rev_col: Optional[str],
    order_id_col: Optional[str],
) -> Tuple[bytes, Dict[str, Any]]:
    """Compiles the full multi-section PDF document into a binary buffer."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=50,
        bottomMargin=50,
    )

    styles = build_pdf_styles()
    story = []
    summary_kpis: Dict[str, Any] = {}

    now = datetime.utcnow()
    report_title = req.title or "Executive Business Performance & Risk Audit"

    # 1. Header Banner
    banner_data = [
        [
            Paragraph("<b>PROFITLENS</b> DECISION INTELLIGENCE", ParagraphStyle("Brand", fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#2563EB"))),
            Paragraph(f"Date: <b>{now.strftime('%B %d, %Y')}</b>", ParagraphStyle("Meta", fontName="Helvetica", fontSize=8, alignment=2, textColor=colors.HexColor("#64748B"))),
        ]
    ]
    banner_table = Table(banner_data, colWidths=[360, 180])
    banner_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=10))

    # Document Title & Context
    story.append(Paragraph(report_title, styles["title"]))
    story.append(
        Paragraph(
            f"Comprehensive quantitative audit for dataset <b>{dataset_name}</b>, covering top-line sales momentum, "
            f"customer churn vulnerability, product catalog health, transaction anomalies, and customer sentiment signals.",
            styles["subtitle"],
        )
    )

    # Compute Core KPIs
    kpis = None
    if date_col and rev_col and date_col in df.columns and rev_col in df.columns:
        kpis, span = compute_executive_kpis(df, date_col, rev_col, order_id_col)
        summary_kpis["total_revenue"] = kpis.total_revenue
        summary_kpis["total_orders"] = kpis.total_orders
        summary_kpis["active_customers"] = kpis.total_customers
        summary_kpis["aov"] = kpis.avg_order_value
        summary_kpis["revenue_growth_pct"] = kpis.revenue_change_pct

    # 2. Executive Scorecard Grid
    story.append(Paragraph("1. Executive KPI Scorecard", styles["h1"]))

    scorecard_rows = []
    if kpis:
        growth_str = f"{kpis.revenue_change_pct:+.1f}%" if kpis.revenue_change_pct is not None else "N/A"
        growth_color = "#059669" if (kpis.revenue_change_pct or 0) >= 0 else "#DC2626"
        scorecard_rows = [
            [
                Paragraph("<b>Total Gross Revenue</b>", styles["td"]),
                Paragraph(f"<b>${kpis.total_revenue:,.2f}</b>", ParagraphStyle("KPI1", fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#0F172A"))),
                Paragraph("<b>Period-over-Period Growth</b>", styles["td"]),
                Paragraph(f"<b>{growth_str}</b>", ParagraphStyle("KPI2", fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor(growth_color))),
            ],
            [
                Paragraph("<b>Total Completed Orders</b>", styles["td"]),
                Paragraph(f"{kpis.total_orders:,}", styles["td_bold"]),
                Paragraph("<b>Average Order Value (AOV)</b>", styles["td"]),
                Paragraph(f"${kpis.avg_order_value:,.2f}", styles["td_bold"]),
            ],
            [
                Paragraph("<b>Active Unique Customers</b>", styles["td"]),
                Paragraph(f"{kpis.total_customers:,}", styles["td_bold"]),
                Paragraph("<b>Observation Days</b>", styles["td"]),
                Paragraph(f"{span.total_days} days", styles["td_bold"]),
            ],
        ]
    else:
        scorecard_rows = [
            [
                Paragraph("<b>Total Rows</b>", styles["td"]),
                Paragraph(f"{len(df):,}", styles["td_bold"]),
                Paragraph("<b>Total Columns</b>", styles["td"]),
                Paragraph(f"{len(df.columns)}", styles["td_bold"]),
            ]
        ]

    scorecard_table = Table(scorecard_rows, colWidths=[140, 130, 140, 130])
    scorecard_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(scorecard_table)
    story.append(Spacer(1, 10))

    # 3. Monthly Financial Trajectory Table
    if date_col and rev_col and date_col in df.columns and rev_col in df.columns:
        _, monthly_series = compute_revenue_timeseries(df, date_col, rev_col, order_id_col)
        if monthly_series:
            story.append(Paragraph("2. Financial Revenue Trajectory (Monthly Breakdown)", styles["h1"]))
            monthly_table_data = [
                [
                    Paragraph("Month", styles["th"]),
                    Paragraph("Gross Revenue", styles["th"]),
                    Paragraph("Order Volume", styles["th"]),
                    Paragraph("AOV", styles["th"]),
                ]
            ]
            # Take last 6 months
            for pt in monthly_series[-6:]:
                aov_val = pt.revenue / max(1, pt.orders)
                monthly_table_data.append([
                    Paragraph(pt.date, styles["td"]),
                    Paragraph(f"${pt.revenue:,.2f}", styles["td_bold"]),
                    Paragraph(f"{pt.orders:,}", styles["td"]),
                    Paragraph(f"${aov_val:.2f}", styles["td"]),
                ])

            m_table = Table(monthly_table_data, colWidths=[120, 150, 130, 140])
            m_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(m_table)
            story.append(Spacer(1, 10))

    # 4. Customer Churn & Retention Vulnerability
    churn_meta = col_meta.get("churn_results")
    if req.include_churn and churn_meta:
        dist = churn_meta.get("risk_distribution", {})
        rev_at_risk = float(churn_meta.get("total_revenue_at_risk", 0.0))
        summary_kpis["revenue_at_risk"] = rev_at_risk
        summary_kpis["critical_churn_count"] = dist.get("critical_count", 0)

        story.append(Paragraph("3. Customer Churn & Retention Vulnerability", styles["h1"]))
        churn_narrative = (
            f"Supervised machine learning evaluation assessed <b>{churn_meta.get('total_customers_evaluated', 0):,}</b> "
            f"active accounts. Identified <b>${rev_at_risk:,.2f}</b> in cumulative revenue at imminent risk of attrition. "
            f"Model ROC-AUC discriminative power: <b>{churn_meta.get('metrics', {}).get('roc_auc', 0.85):.3f}</b>."
        )
        story.append(Paragraph(churn_narrative, styles["body"]))

        churn_table_data = [
            [
                Paragraph("Risk Tier", styles["th"]),
                Paragraph("Customer Count", styles["th"]),
                Paragraph("Cohort Percentage", styles["th"]),
                Paragraph("Recommended Intervention", styles["th"]),
            ],
            [
                Paragraph("<b>Critical Risk</b>", styles["td"]),
                Paragraph(f"{dist.get('critical_count', 0):,}", styles["td_bold"]),
                Paragraph(f"{dist.get('critical_pct', 0):.1f}%", styles["td"]),
                Paragraph("Immediate VIP account manager outreach + bespoke retention incentive", styles["td"]),
            ],
            [
                Paragraph("<b>High Risk</b>", styles["td"]),
                Paragraph(f"{dist.get('high_count', 0):,}", styles["td_bold"]),
                Paragraph(f"{dist.get('high_pct', 0):.1f}%", styles["td"]),
                Paragraph("Automated reactivation email sequence with 15% discount voucher", styles["td"]),
            ],
            [
                Paragraph("<b>Medium Risk</b>", styles["td"]),
                Paragraph(f"{dist.get('medium_count', 0):,}", styles["td_bold"]),
                Paragraph(f"{dist.get('medium_pct', 0):.1f}%", styles["td"]),
                Paragraph("Personalized product recommendation push notifications", styles["td"]),
            ],
            [
                Paragraph("<b>Low Risk</b>", styles["td"]),
                Paragraph(f"{dist.get('low_count', 0):,}", styles["td_bold"]),
                Paragraph(f"{dist.get('low_pct', 0):.1f}%", styles["td"]),
                Paragraph("Standard loyalty reward program cadence", styles["td"]),
            ],
        ]
        c_table = Table(churn_table_data, colWidths=[90, 85, 95, 270])
        c_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7C3AED")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(c_table)
        story.append(Spacer(1, 10))

    # 5. Product Catalog BCG Growth-Share Matrix
    product_meta = col_meta.get("product_intelligence")
    if req.include_products and product_meta:
        bcg_dist = product_meta.get("bcg_distribution", {})
        story.append(Paragraph("4. Product Catalog Intelligence & BCG Matrix", styles["h1"]))

        story.append(
            Paragraph(
                f"Strategic portfolio evaluation across <b>{product_meta.get('total_products', 0):,} SKUs</b> "
                f"generating <b>${product_meta.get('total_revenue', 0.0):,.2f}</b> gross merchandise value. "
                f"Identified catalog distribution across market growth and relative category share:",
                styles["body"],
            )
        )

        bcg_table_data = [
            [
                Paragraph("BCG Quadrant", styles["th"]),
                Paragraph("SKU Count", styles["th"]),
                Paragraph("Gross Revenue", styles["th"]),
                Paragraph("Strategic Directive", styles["th"]),
            ],
            [
                Paragraph("<b>Stars (High Growth, High Share)</b>", styles["td"]),
                Paragraph(f"{bcg_dist.get('stars_count', 0):,}", styles["td_bold"]),
                Paragraph(f"${bcg_dist.get('stars_revenue', 0.0):,.2f}", styles["td_bold"]),
                Paragraph("Scale ad spend, secure buffer stock, expand capacity", styles["td"]),
            ],
            [
                Paragraph("<b>Cash Cows (Low Growth, High Share)</b>", styles["td"]),
                Paragraph(f"{bcg_dist.get('cash_cows_count', 0):,}", styles["td_bold"]),
                Paragraph(f"${bcg_dist.get('cash_cows_revenue', 0.0):,.2f}", styles["td_bold"]),
                Paragraph("Harvest margins, optimize supply chain efficiency", styles["td"]),
            ],
            [
                Paragraph("<b>Question Marks (High Growth, Low Share)</b>", styles["td"]),
                Paragraph(f"{bcg_dist.get('question_marks_count', 0):,}", styles["td_bold"]),
                Paragraph(f"${bcg_dist.get('question_marks_revenue', 0.0):,.2f}", styles["td_bold"]),
                Paragraph("Selective test marketing or repositioning", styles["td"]),
            ],
            [
                Paragraph("<b>Dogs (Low Growth, Low Share)</b>", styles["td"]),
                Paragraph(f"{bcg_dist.get('dogs_count', 0):,}", styles["td_bold"]),
                Paragraph(f"${bcg_dist.get('dogs_revenue', 0.0):,.2f}", styles["td_bold"]),
                Paragraph("Phase out, discount clearance, eliminate holding cost", styles["td"]),
            ],
        ]
        p_table = Table(bcg_table_data, colWidths=[150, 65, 105, 220])
        p_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284C7")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(p_table)
        story.append(Spacer(1, 10))

    # 6. Transaction Anomaly & Fraud Audit Log
    anomaly_meta = col_meta.get("anomaly_results")
    if req.include_anomalies and anomaly_meta:
        dist = anomaly_meta.get("distribution", {})
        total_flagged_rev = float(dist.get("total_flagged_revenue", 0.0))
        summary_kpis["anomalies_flagged"] = dist.get("total_anomalies", 0)
        summary_kpis["flagged_revenue"] = total_flagged_rev

        story.append(Paragraph("5. Transaction Anomaly & Fraud Diagnostics", styles["h1"]))
        story.append(
            Paragraph(
                f"Isolation Forest path length and Median Absolute Deviation (MAD) scanning inspected <b>{anomaly_meta.get('total_orders_scanned', 0):,}</b> "
                f"orders. Flagged <b>{dist.get('total_anomalies', 0):,}</b> outlier transactions representing "
                f"<b>${total_flagged_rev:,.2f}</b> in flagged transaction value (Critical: {dist.get('critical_count', 0)}, High: {dist.get('high_count', 0)}).",
                styles["body"],
            )
        )

        # Top anomalies table
        anomalies_list = anomaly_meta.get("top_anomalies", [])
        if anomalies_list:
            ano_table_data = [
                [
                    Paragraph("Order ID", styles["th"]),
                    Paragraph("Date", styles["th"]),
                    Paragraph("Amount", styles["th"]),
                    Paragraph("Severity", styles["th"]),
                    Paragraph("Detection Root Cause", styles["th"]),
                ]
            ]
            for item in anomalies_list[:5]:
                sev_color = "#DC2626" if item.get("severity") in ["critical", "high"] else "#D97706"
                ano_table_data.append([
                    Paragraph(str(item.get("order_id")), styles["td"]),
                    Paragraph(str(item.get("order_date"))[:10], styles["td"]),
                    Paragraph(f"${float(item.get('amount', 0)):,.2f}", styles["td_bold"]),
                    Paragraph(f"<b>{item.get('severity', '').upper()}</b>", ParagraphStyle("Sev", fontName="Helvetica-Bold", fontSize=7, textColor=colors.HexColor(sev_color))),
                    Paragraph(str(item.get("reason")), styles["td"]),
                ])

            a_table = Table(ano_table_data, colWidths=[90, 75, 85, 70, 220])
            a_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DC2626")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(a_table)
            story.append(Spacer(1, 10))

    # 7. Customer Sentiment & Review Analysis
    sentiment_meta = col_meta.get("sentiment_analysis")
    if req.include_sentiment and sentiment_meta:
        dist = sentiment_meta.get("distribution", {})
        nss = float(dist.get("net_sentiment_score", 0.0))
        summary_kpis["net_sentiment_score"] = nss

        story.append(Paragraph("6. Customer Feedback & Net Sentiment Index", styles["h1"]))
        story.append(
            Paragraph(
                f"Natural Language Processing scanned <b>{dist.get('total_reviews', 0):,}</b> customer reviews. "
                f"Net Sentiment Score (NSS): <b>{nss:+.1f}%</b> (Positive: {dist.get('positive_count', 0)}, "
                f"Neutral: {dist.get('neutral_count', 0)}, Negative: {dist.get('negative_count', 0)}). "
                f"Average Star Rating: <b>{dist.get('avg_rating', 0.0):.2f} / 5.0</b>.",
                styles["body"],
            )
        )

        aspects = sentiment_meta.get("aspects", [])
        if aspects:
            asp_table_data = [
                [
                    Paragraph("Operational Aspect", styles["th"]),
                    Paragraph("Mentions", styles["th"]),
                    Paragraph("Polarity Score", styles["th"]),
                    Paragraph("Status", styles["th"]),
                ]
            ]
            for asp in aspects:
                score = float(asp.get("avg_sentiment_score", 0.0))
                score_color = "#059669" if score >= 0.1 else ("#DC2626" if score <= -0.1 else "#D97706")
                asp_table_data.append([
                    Paragraph(f"<b>{asp.get('aspect')}</b>", styles["td"]),
                    Paragraph(f"{asp.get('total_mentions', 0):,}", styles["td"]),
                    Paragraph(f"{score:+.2f}", ParagraphStyle("Score", fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor(score_color))),
                    Paragraph(str(asp.get("sentiment_label")).replace("_", " ").title(), styles["td"]),
                ])

            s_table = Table(asp_table_data, colWidths=[150, 90, 110, 190])
            s_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DB2777")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(s_table)
            story.append(Spacer(1, 10))

    # 8. Prescriptive Strategic Action Plan
    story.append(Paragraph("7. Prescriptive Operational Recommendations", styles["h1"]))
    recommendations = [
        "1. <b>Customer Retention</b>: Prioritize direct outreach to Critical-Tier churn accounts with personalized retention incentives to protect recurring cash flows.",
        "2. <b>Catalog Optimization</b>: Double marketing allocation toward high-velocity 'Star' products while initiating inventory markdowns for 'Dog' SKUs.",
        "3. <b>Risk Governance</b>: Review unresolved critical anomaly orders in the triage queue to verify gateway authentication integrity and limit chargeback exposure.",
        "4. <b>Customer Experience</b>: Address negative feedback clusters in shipping and fulfillment to improve overall Net Sentiment Score and repurchase rates.",
    ]
    for rec in recommendations:
        story.append(Paragraph(rec, styles["body"]))

    # Build Document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue(), summary_kpis


def generate_csv_export_content(
    dataset_name: str,
    df: pd.DataFrame,
    col_meta: Dict[str, Any],
    date_col: Optional[str],
    rev_col: Optional[str],
    order_id_col: Optional[str],
) -> Tuple[bytes, Dict[str, Any]]:
    """Compiles a consolidated financial and operational CSV audit sheet."""
    output = io.StringIO()
    summary_kpis: Dict[str, Any] = {}

    output.write(f"# ProfitLens Executive Intelligence CSV Export\n")
    output.write(f"# Dataset: {dataset_name}\n")
    output.write(f"# Export Date: {datetime.utcnow().isoformat()}\n\n")

    # Section 1: Core KPIs
    output.write("--- EXECUTIVE METRICS ---\n")
    if date_col and rev_col and date_col in df.columns and rev_col in df.columns:
        kpis, _ = compute_executive_kpis(df, date_col, rev_col, order_id_col)
        summary_kpis["total_revenue"] = kpis.total_revenue
        summary_kpis["total_orders"] = kpis.total_orders
        summary_kpis["active_customers"] = kpis.total_customers
        summary_kpis["aov"] = kpis.avg_order_value
        summary_kpis["growth_pct"] = kpis.revenue_change_pct

        output.write(f"Metric,Value\n")
        output.write(f"Total Revenue,${kpis.total_revenue:.2f}\n")
        output.write(f"Total Orders,{kpis.total_orders}\n")
        output.write(f"Active Customers,{kpis.total_customers}\n")
        output.write(f"Average Order Value,${kpis.avg_order_value:.2f}\n")
        output.write(f"Period Growth Rate,{kpis.revenue_change_pct or 0.0:.2f}%\n\n")

    # Section 2: Monthly Breakdown
    if date_col and rev_col and date_col in df.columns and rev_col in df.columns:
        output.write("--- MONTHLY PERFORMANCE ---\n")
        _, monthly = compute_revenue_timeseries(df, date_col, rev_col, order_id_col)
        output.write("Month,Revenue,OrderCount,AOV\n")
        for pt in monthly:
            pt_aov = pt.revenue / max(1, pt.orders)
            output.write(f"{pt.date},{pt.revenue:.2f},{pt.orders},{pt_aov:.2f}\n")
        output.write("\n")

    # Section 3: Anomaly Summary
    ano_meta = col_meta.get("anomaly_results")
    if ano_meta:
        output.write("--- TRANSACTION ANOMALY TRIAGE ---\n")
        dist = ano_meta.get("distribution", {})
        output.write(f"Total Anomalies Flagged,{dist.get('total_anomalies', 0)}\n")
        output.write(f"Flagged Revenue,${dist.get('total_flagged_revenue', 0.0):.2f}\n")
        output.write("OrderID,Date,Amount,Severity,Reason\n")
        for item in ano_meta.get("top_anomalies", []):
            output.write(
                f"{item.get('order_id')},{item.get('order_date')},{item.get('amount')},{item.get('severity')},\"{item.get('reason')}\"\n"
            )
        output.write("\n")

    content_bytes = output.getvalue().encode("utf-8")
    return content_bytes, summary_kpis


async def generate_dataset_report(
    dataset_id: str,
    organization_id: str,
    request: ReportGenerateRequest,
    db: AsyncIOMotorDatabase,
) -> ReportMetadataItem:
    """Orchestrates multi-format report generation and persistence in MongoDB."""
    doc = await db.datasets.find_one({
        "$or": [{"id": str(dataset_id)}, {"_id": str(dataset_id)}],
        "organization_id": str(organization_id),
    })
    if not doc:
        raise ValueError(f"Dataset {dataset_id} not found")
    dataset = Dataset.from_doc(doc)
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} not found")

    col_meta = dict(dataset.column_metadata or {})
    raw_df = load_dataset_as_dataframe(dataset)

    # Resolve column roles
    suggestions = get_dataset_mapping_suggestions(raw_df)
    mappings = dataset.column_mappings or {}

    def get_col(role: str) -> Optional[str]:
        if role in mappings and mappings[role] in raw_df.columns:
            return mappings[role]
        for s in suggestions:
            if s.suggested_role == role and s.confidence >= 0.6:
                return s.column_name
        return None

    date_col = get_col("order_date")
    rev_col = get_col("revenue")
    order_id_col = get_col("order_id")

    report_id = str(uuid.uuid4())
    file_ext = "pdf" if request.format == "pdf" else "csv"
    file_name = f"{dataset_id}_{report_id}.{file_ext}"
    file_path = os.path.join(REPORTS_DIR, file_name)

    now_iso = datetime.utcnow().isoformat()
    report_title = request.title or (
        "Executive Business Intelligence Report" if request.format == "pdf" else "Financial Audit Data Export"
    )

    if request.format == "pdf":
        file_bytes, summary_kpis = generate_executive_pdf_content(
            dataset_name=dataset.name,
            df=raw_df,
            col_meta=col_meta,
            req=request,
            date_col=date_col,
            rev_col=rev_col,
            order_id_col=order_id_col,
        )
    else:
        file_bytes, summary_kpis = generate_csv_export_content(
            dataset_name=dataset.name,
            df=raw_df,
            col_meta=col_meta,
            date_col=date_col,
            rev_col=rev_col,
            order_id_col=order_id_col,
        )

    # Write to disk
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    file_size = len(file_bytes)

    item = ReportMetadataItem(
        id=report_id,
        dataset_id=dataset_id,
        report_name=report_title,
        report_type=request.report_type,
        format=request.format,
        file_path=file_path,
        file_size_bytes=file_size,
        status="completed",
        summary_kpis=summary_kpis,
        created_at=now_iso,
    )

    # Save to dataset metadata in MongoDB
    existing_reports = list(col_meta.get("generated_reports", []))
    existing_reports.insert(0, item.model_dump())
    col_meta["generated_reports"] = existing_reports

    await db.datasets.update_one(
        {"$or": [{"id": dataset.id}, {"_id": dataset.id}]},
        {"$set": {
            "column_metadata": col_meta,
            "updated_at": datetime.utcnow(),
        }}
    )

    return item


async def list_dataset_reports(
    dataset_id: str,
    organization_id: str,
    db: AsyncIOMotorDatabase,
) -> ReportListResponse:
    """Retrieves metadata history of all reports compiled for a dataset in MongoDB."""
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
    raw_list = col_meta.get("generated_reports", [])

    reports: List[ReportMetadataItem] = []
    for r in raw_list:
        try:
            reports.append(ReportMetadataItem(**r))
        except Exception:
            continue

    return ReportListResponse(
        dataset_id=dataset_id,
        reports=reports,
        total=len(reports),
    )


async def get_report_file_path(
    dataset_id: str,
    report_id: str,
    organization_id: str,
    db: AsyncIOMotorDatabase,
) -> Tuple[str, str, str]:
    """Resolves the physical file path, filename, and MIME type for report download from MongoDB."""
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
    raw_list = col_meta.get("generated_reports", [])

    target_report = None
    for r in raw_list:
        if r.get("id") == report_id:
            target_report = r
            break

    if not target_report:
        raise ValueError(f"Report {report_id} not found")

    file_path = target_report.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise ValueError(f"Report file on disk could not be located")

    fmt = target_report.get("format", "pdf")
    mime = "application/pdf" if fmt == "pdf" else "text/csv"
    download_filename = f"{target_report.get('report_name', 'Report').replace(' ', '_')}.{fmt}"

    return file_path, download_filename, mime
