"""Phase 18: Master End-to-End Analytics Pipeline Integration Test.

Validates the complete execution flow across all 18 phases of ProfitLens:
Dataset Ingestion -> Profiling -> Mapping -> Cleaning -> Feature Engineering ->
Executive KPIs -> Customer Segmentation -> Churn Prediction -> Sales Forecasting ->
Anomaly Detection -> Product BCG Matrix -> Sentiment NLP -> Executive Insights ->
Corporate Report Generation.
"""

import os
import io
import pytest
import pandas as pd
import numpy as np

# Phase 5: Profiling
from app.services.profiling_service import profile_dataframe, match_potential_role

# Phase 6: Mapping
from app.services.mapping_service import (
    generate_suggested_mappings,
    validate_mapped_schema,
)

# Phase 7: Cleaning
from app.services.cleaning_service import (
    execute_cleaning_pipeline,
    winsorize_iqr,
)

# Phase 8: Features
from app.services.feature_service import (
    compute_customer_rfm_features,
    compute_timeseries_features,
)

# Phase 9: BI KPIs
from app.services.analytics_service import (
    compute_executive_kpis,
    compute_revenue_timeseries,
    compute_category_breakdown,
    compute_top_products,
)

# Phase 10: Segmentation
from app.services.segmentation_service import (
    preprocess_customer_features,
    evaluate_optimal_k,
    generate_segment_personas,
)
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

# Phase 11: Churn
from app.services.churn_service import (
    prepare_churn_features_and_target,
    train_churn_classifier,
    score_customer_churn_risks,
)

# Phase 12: Forecasting
from app.services.forecast_service import (
    resample_daily_revenue_series,
    fit_and_forecast_models,
)

# Phase 13: Anomalies
from app.services.anomaly_service import (
    compute_anomaly_features,
    run_isolation_and_mad_scoring,
    synthesize_anomaly_explanations,
)

# Phase 14: Products & BCG
from app.services.product_intelligence_service import (
    compute_product_metrics,
    compute_product_growth_rates,
    classify_bcg_quadrants,
    compute_product_pareto_curve,
)

# Phase 15: Sentiment & NLP
from app.services.sentiment_service import (
    process_reviews_dataframe,
)

# Phase 16: Insights
from app.services.insights_service import (
    evaluate_revenue_insights,
    evaluate_churn_insights,
    evaluate_anomaly_insights,
    evaluate_product_insights,
    evaluate_sentiment_insights,
)

# Phase 17: Reports
from app.services.report_service import (
    generate_executive_pdf_content,
    generate_csv_export_content,
)
from app.schemas.reports import ReportGenerateRequest


@pytest.fixture
def master_synthetic_enterprise_df():
    """Generates a realistic multi-attribute enterprise transaction DataFrame with active and churned customers."""
    np.random.seed(42)
    dates = pd.date_range("2025-11-01", periods=90, freq="D")
    categories = ["Electronics", "Office Furniture", "Home Audio", "Computer Accessories"]
    products = [f"SKU-{i:03d}" for i in range(12)]

    records = []
    # 1. 15 Loyalists (transact across all 90 days)
    for i in range(15):
        cid = f"CUST-{i:03d}"
        for _ in range(np.random.randint(5, 10)):
            d = np.random.choice(dates)
            records.append({
                "order_id": f"ORD-{len(records):05d}",
                "order_date": d,
                "revenue": round(float(np.random.uniform(40.0, 300.0)), 2),
                "customer_id": cid,
                "product_id": np.random.choice(products),
                "category": np.random.choice(categories),
                "quantity": np.random.randint(1, 5),
                "discount": float(np.random.choice([0.0, 0.05, 0.1])),
            })

    # 2. 10 Churned Customers (only purchased in days 0-25)
    early_dates = dates[:25]
    for i in range(15, 25):
        cid = f"CUST-{i:03d}"
        for _ in range(np.random.randint(2, 5)):
            d = np.random.choice(early_dates)
            records.append({
                "order_id": f"ORD-{len(records):05d}",
                "order_date": d,
                "revenue": round(float(np.random.uniform(25.0, 150.0)), 2),
                "customer_id": cid,
                "product_id": np.random.choice(products),
                "category": np.random.choice(categories),
                "quantity": np.random.randint(1, 3),
                "discount": 0.0,
            })

    df = pd.DataFrame(records)
    # Inject 2 high-value anomalies
    df.loc[10, "revenue"] = 2850.0
    df.loc[35, "revenue"] = 3200.0
    return df


@pytest.fixture
def master_synthetic_reviews_df():
    """Generates synthetic customer reviews for ABSA NLP testing."""
    return pd.DataFrame({
        "customer_id": [f"CUST-{i % 25:03d}" for i in range(40)],
        "product_id": [f"SKU-{i % 12:03d}" for i in range(40)],
        "review_text": [
            "Outstanding quality, extremely durable and arrived super fast!" if i % 4 == 0 else
            "Terrible customer service and delayed shipping, broken on arrival." if i % 4 == 1 else
            "Decent product for the price, works as expected." if i % 4 == 2 else
            "The packaging was damaged, but the product itself is excellent."
            for i in range(40)
        ],
        "rating": [5 if i % 4 == 0 else (1 if i % 4 == 1 else (3 if i % 4 == 2 else 4)) for i in range(40)],
    })


def test_complete_profitlens_pipeline_execution(
    master_synthetic_enterprise_df, master_synthetic_reviews_df
):
    """Executes the full ProfitLens intelligence pipeline sequentially from raw data to PDF report."""
    raw_df = master_synthetic_enterprise_df
    n_rows = len(raw_df)

    # 1. Profiling & Quality Assessment
    profile = profile_dataframe(raw_df, dataset_id="test-ds-1", dataset_name="enterprise_orders.csv")
    assert profile.row_count == n_rows
    assert profile.column_count == 8
    assert profile.quality_score >= 80.0

    # 2. Intelligent Column Mapping
    suggestions = generate_suggested_mappings(list(raw_df.columns))
    mappings = {s.canonical_field: s.mapped_column for s in suggestions if s.confidence >= 0.6}
    assert "order_date" in mappings
    assert "revenue" in mappings
    readiness = validate_mapped_schema(mappings)
    assert readiness.is_valid_for_basic_analytics is True

    # 3. Data Cleaning Pipeline
    from app.schemas.dataset import CleaningStrategyConfig
    config = CleaningStrategyConfig(handle_duplicates=True)
    cleaned_df, actions, orig_missing, clean_missing = execute_cleaning_pipeline(
        raw_df, mappings, config
    )
    assert len(cleaned_df) == n_rows

    # 4. Feature Engineering
    rfm_df, _ = compute_customer_rfm_features(
        cleaned_df,
        customer_id_col="customer_id",
        date_col="order_date",
        revenue_col="revenue",
        order_id_col="order_id",
    )
    assert len(rfm_df) == 25
    assert "recency_days" in rfm_df.columns
    assert "frequency" in rfm_df.columns
    assert "monetary_total" in rfm_df.columns

    # 5. Executive BI KPIs
    kpis, span = compute_executive_kpis(cleaned_df, "order_date", "revenue", "order_id", "customer_id")
    assert kpis.total_revenue > 0
    assert kpis.total_orders == n_rows
    assert kpis.total_customers == 25
    assert span.total_days > 0

    daily_series, monthly_series = compute_revenue_timeseries(cleaned_df, "order_date", "revenue", "order_id")
    assert len(daily_series) > 0
    assert len(monthly_series) > 0

    # 6. Customer Segmentation (k-Means & PCA)
    feat_matrix, feat_cols = preprocess_customer_features(rfm_df)
    elbow_points, optimal_k = evaluate_optimal_k(feat_matrix, max_k=4)
    assert optimal_k in [2, 3, 4]

    km = KMeans(n_clusters=optimal_k, init="k-means++", random_state=42, n_init=10)
    rfm_df["cluster"] = km.fit_predict(feat_matrix)
    personas = generate_segment_personas(rfm_df, cluster_col="cluster")
    assert len(personas) == optimal_k

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(feat_matrix)
    assert coords.shape == (25, 2)

    # 7. Customer Churn Prediction
    churn_X, churn_y, current_df, feature_cols = prepare_churn_features_and_target(
        raw_df=cleaned_df,
        customer_id_col="customer_id",
        date_col="order_date",
        revenue_col="revenue",
        inactivity_days=30,
    )
    clf, churn_metrics, top_features, model_used = train_churn_classifier(
        X=churn_X, y=churn_y, model_type="auto"
    )
    assert churn_metrics.roc_auc >= 0.50

    churn_scored, churn_dist, rev_at_risk = score_customer_churn_risks(
        model=clf,
        current_df=current_df,
        feature_cols=feature_cols,
    )
    assert len(churn_scored) == 25

    # 8. Sales Forecasting
    daily_ts = resample_daily_revenue_series(cleaned_df, "order_date", "revenue")
    f_vals, lowers, uppers, f_metrics, model_name = fit_and_forecast_models(
        daily_ts, horizon_days=14, confidence_level=0.95, model_type="auto"
    )
    assert len(f_vals) == 14
    assert sum(f_vals) > 0

    # 9. Transaction Anomaly & Fraud Detection
    X_anom, data_anom, feat_cols = compute_anomaly_features(
        cleaned_df, "order_id", "order_date", "revenue", "customer_id", "quantity", "category"
    )
    scored_anom_df = run_isolation_and_mad_scoring(
        X=X_anom,
        data=data_anom,
        revenue_col="revenue",
        contamination=0.05,
    )
    assert len(scored_anom_df) == n_rows
    assert "anomaly_score" in scored_anom_df.columns
    # Synthesize explanations across scored transactions
    critical_or_high = []
    for _, row in scored_anom_df.iterrows():
        sev, reason, details = synthesize_anomaly_explanations(row, revenue_col="revenue")
        if sev in ["critical", "high"]:
            critical_or_high.append({
                "order_id": row["order_id"],
                "amount": float(row["revenue"]),
                "severity": sev,
                "reason": reason,
                "score": float(row["anomaly_score"]),
            })
    # Artificial spikes must be flagged with critical or high severity
    assert len(critical_or_high) > 0

    # 10. Product Catalog Intelligence & BCG Matrix
    prod_metrics = compute_product_metrics(
        cleaned_df,
        product_id_col="product_id",
        revenue_col="revenue",
        date_col="order_date",
        quantity_col="quantity",
    )
    assert len(prod_metrics) == 12
    growth_rates = compute_product_growth_rates(
        cleaned_df,
        product_id_col="product_id",
        revenue_col="revenue",
        date_col="order_date",
    )
    bcg_df = classify_bcg_quadrants(
        prod_metrics,
        growth_rates=growth_rates,
        product_id_col="product_id",
    )
    assert len(bcg_df) == 12
    pareto_df, pareto_pts = compute_product_pareto_curve(
        prod_metrics,
        product_id_col="product_id",
    )
    assert len(pareto_pts) == 12

    # 11. Customer Sentiment & Review NLP
    reviews_df = master_synthetic_reviews_df
    sentiment_dist, aspects, keywords, review_items = process_reviews_dataframe(
        reviews_df, "review_text", "rating", "customer_id", "product_id"
    )
    assert sentiment_dist.total_reviews == 40
    assert len(aspects) == 4
    assert len(keywords) > 0

    # 12. Automated Executive Insights Synthesis
    bcg_distribution = {
        "stars_count": sum(1 for _, r in bcg_df.iterrows() if r["bcg_category"] == "star"),
        "cash_cows_count": sum(1 for _, r in bcg_df.iterrows() if r["bcg_category"] == "cash_cow"),
        "question_marks_count": sum(1 for _, r in bcg_df.iterrows() if r["bcg_category"] == "question_mark"),
        "dogs_count": sum(1 for _, r in bcg_df.iterrows() if r["bcg_category"] == "dog"),
    }

    col_meta = {
        "churn_results": {
            "total_customers_evaluated": len(churn_scored),
            "total_revenue_at_risk": rev_at_risk,
            "metrics": churn_metrics.model_dump(),
            "risk_distribution": churn_dist.model_dump(),
        },
        "anomaly_results": {
            "total_orders_scanned": n_rows,
            "distribution": {
                "total_anomalies": len(critical_or_high),
                "total_flagged_revenue": sum(e["amount"] for e in critical_or_high),
                "critical_count": sum(1 for e in critical_or_high if e["severity"] == "critical"),
                "high_count": sum(1 for e in critical_or_high if e["severity"] == "high"),
            },
            "top_anomalies": critical_or_high[:5],
        },
        "product_intelligence": {
            "total_products": len(bcg_df),
            "total_revenue": float(bcg_df["revenue"].sum()),
            "bcg_distribution": bcg_distribution,
        },
        "sentiment_analysis": {
            "distribution": sentiment_dist.model_dump(),
            "aspects": [a.model_dump() for a in aspects],
        },
    }

    rev_insights = evaluate_revenue_insights(col_meta, cleaned_df, "order_date", "revenue", "order_id")
    churn_insights = evaluate_churn_insights(col_meta)
    ano_insights = evaluate_anomaly_insights(col_meta)
    prod_insights = evaluate_product_insights(col_meta)
    sent_insights = evaluate_sentiment_insights(col_meta)

    all_insights = rev_insights + churn_insights + ano_insights + prod_insights + sent_insights
    assert len(all_insights) > 0

    # Priority sorting
    sev_weights = {"critical": 4, "warning": 3, "positive": 2, "info": 1}
    sorted_insights = sorted(
        all_insights,
        key=lambda x: (sev_weights.get(x.severity, 0), x.impact_score),
        reverse=True,
    )
    assert sorted_insights[0].severity in ["critical", "warning", "positive"]

    # 13. Multi-Format Corporate Report Generation
    req = ReportGenerateRequest(
        report_type="executive_summary",
        format="pdf",
        title="ProfitLens Enterprise Comprehensive Audit",
        include_churn=True,
        include_anomalies=True,
        include_products=True,
        include_sentiment=True,
    )

    pdf_bytes, report_kpis = generate_executive_pdf_content(
        dataset_name="Enterprise Corp 2026",
        df=cleaned_df,
        col_meta=col_meta,
        req=req,
        date_col="order_date",
        rev_col="revenue",
        order_id_col="order_id",
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2500
    assert pdf_bytes.startswith(b"%PDF")
    assert report_kpis["total_orders"] == n_rows

    csv_bytes, csv_kpis = generate_csv_export_content(
        dataset_name="Enterprise Corp 2026",
        df=cleaned_df,
        col_meta=col_meta,
        date_col="order_date",
        rev_col="revenue",
        order_id_col="order_id",
    )
    assert isinstance(csv_bytes, bytes)
    assert len(csv_bytes) > 500
    assert b"ProfitLens Executive Intelligence CSV Export" in csv_bytes
