"""Unit tests for Customer Segmentation and K-Means Clustering Service."""

import pytest
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from app.services.segmentation_service import (
    preprocess_customer_features,
    evaluate_optimal_k,
    generate_segment_personas,
)


@pytest.fixture
def sample_customer_features():
    """Generate a realistic sample of 40 customers across distinct behavioral profiles."""
    np.random.seed(42)
    
    # 1. VIPs: Low recency (1-10d), High freq (8-15), High spend ($800-$2000)
    vips = pd.DataFrame({
        "customer_id": [f"VIP-{i}" for i in range(10)],
        "recency_days": np.random.randint(1, 10, size=10),
        "frequency": np.random.randint(8, 16, size=10),
        "monetary_total": np.random.uniform(800.0, 2000.0, size=10).round(2),
        "avg_order_value": np.random.uniform(100.0, 150.0, size=10).round(2),
        "customer_lifespan_days": np.random.randint(100, 300, size=10),
    })

    # 2. Loyal Regulars: Moderate recency (15-40d), Moderate freq (4-7), Moderate spend ($200-$600)
    loyals = pd.DataFrame({
        "customer_id": [f"LOYAL-{i}" for i in range(10)],
        "recency_days": np.random.randint(15, 40, size=10),
        "frequency": np.random.randint(4, 8, size=10),
        "monetary_total": np.random.uniform(200.0, 600.0, size=10).round(2),
        "avg_order_value": np.random.uniform(50.0, 80.0, size=10).round(2),
        "customer_lifespan_days": np.random.randint(60, 200, size=10),
    })

    # 3. New / Promising: Low recency (2-14d), Low freq (1-2), Low spend ($30-$100)
    news = pd.DataFrame({
        "customer_id": [f"NEW-{i}" for i in range(10)],
        "recency_days": np.random.randint(2, 15, size=10),
        "frequency": np.random.randint(1, 3, size=10),
        "monetary_total": np.random.uniform(30.0, 100.0, size=10).round(2),
        "avg_order_value": np.random.uniform(30.0, 50.0, size=10).round(2),
        "customer_lifespan_days": np.random.randint(0, 20, size=10),
    })

    # 4. At Risk / Inactive: High recency (90-250d), Low freq (1-3), Low spend ($40-$150)
    at_risk = pd.DataFrame({
        "customer_id": [f"RISK-{i}" for i in range(10)],
        "recency_days": np.random.randint(90, 250, size=10),
        "frequency": np.random.randint(1, 4, size=10),
        "monetary_total": np.random.uniform(40.0, 150.0, size=10).round(2),
        "avg_order_value": np.random.uniform(30.0, 50.0, size=10).round(2),
        "customer_lifespan_days": np.random.randint(10, 80, size=10),
    })

    return pd.concat([vips, loyals, news, at_risk], ignore_index=True)


def test_preprocess_customer_features(sample_customer_features):
    """Verify log-scaling and standard scaling zero mean / unit variance properties."""
    X_scaled, feature_cols = preprocess_customer_features(sample_customer_features)
    
    assert X_scaled.shape == (40, 5)
    assert feature_cols == ["recency_days", "frequency", "monetary_total", "avg_order_value", "customer_lifespan_days"]
    
    # Each column should have approximate mean ~ 0 and std ~ 1
    means = np.mean(X_scaled, axis=0)
    stds = np.std(X_scaled, axis=0)
    
    for m in means:
        assert abs(m) < 1e-6
    for s in stds:
        assert abs(s - 1.0) < 1e-6


def test_evaluate_optimal_k(sample_customer_features):
    """Verify elbow points generation and optimal k selection."""
    X_scaled, _ = preprocess_customer_features(sample_customer_features)
    elbow_curve, best_k = evaluate_optimal_k(X_scaled, max_k=5)
    
    assert len(elbow_curve) == 4  # k=2, 3, 4, 5
    assert best_k in [3, 4, 5]
    
    # Inertia should strictly decrease as k increases
    inertias = [p.inertia for p in elbow_curve]
    for i in range(len(inertias) - 1):
        assert inertias[i] >= inertias[i + 1]

    # Silhouette score should be bounded in [-1, 1]
    for p in elbow_curve:
        assert -1.0 <= p.silhouette <= 1.0


def test_generate_segment_personas(sample_customer_features):
    """Verify persona assignment, strategy recommendations, and metric aggregations."""
    X_scaled, _ = preprocess_customer_features(sample_customer_features)
    kmeans = KMeans(n_clusters=4, init="k-means++", random_state=42, n_init=10)
    sample_customer_features["cluster"] = kmeans.fit_predict(X_scaled)
    
    profiles = generate_segment_personas(sample_customer_features, cluster_col="cluster")
    
    assert len(profiles) == 4
    labels = {p.label for p in profiles}
    
    # At least Champions and At Risk / Inactive should be identified
    assert "Champions & VIPs" in labels
    assert "At Risk & Inactive" in labels

    # Sum of customer percentages should equal ~100%
    total_pct = sum(p.percentage for p in profiles)
    assert abs(total_pct - 100.0) < 1.0

    # Each profile must have valid actionable strategy
    for p in profiles:
        assert len(p.strategy_recommendation) > 10
        assert p.color.startswith("#")
        assert p.avg_monetary > 0


def test_pca_projection_and_variance(sample_customer_features):
    """Verify that PCA reduces 5D RFM features to 2 orthogonal components capturing > 60% variance."""
    X_scaled, _ = preprocess_customer_features(sample_customer_features)
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X_scaled)
    
    assert coords.shape == (40, 2)
    
    var_ratio = pca.explained_variance_ratio_
    assert len(var_ratio) == 2
    # Combined variance explained by top 2 components should exceed 60%
    assert sum(var_ratio) > 0.60
    
    # Orthogonality check: dot product of components close to 0
    dot_prod = np.dot(pca.components_[0], pca.components_[1])
    assert abs(dot_prod) < 1e-10

