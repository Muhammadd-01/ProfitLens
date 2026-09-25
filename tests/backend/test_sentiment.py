"""Unit tests for Customer Sentiment & Review NLP Service."""

import pytest
import pandas as pd
from app.services.sentiment_service import (
    compute_sentiment_score,
    detect_aspects,
    extract_keywords_tfidf,
    process_reviews_dataframe,
)


def test_compute_sentiment_score_positives():
    """Verify polarity scoring on commercial positive customer reviews."""
    pos_reviews = [
        "Love this.",
        "Great product!",
        "Fantastic quality.",
        "Exceeded expectations.",
        "Very satisfied.",
        "Worth every penny.",
        "Five stars!",
    ]

    for rev in pos_reviews:
        score, label = compute_sentiment_score(rev)
        assert label == "positive", f"Expected positive for '{rev}', got {label} with score {score}"
        assert score > 0.05


def test_compute_sentiment_score_negatives():
    """Verify polarity scoring on commercial negative customer reviews including negations."""
    neg_reviews = [
        "Poor quality.",
        "Arrived damaged.",
        "Terrible.",
        "Broken on arrival, waste of money.",
        "Not good, very disappointed.",
        "Horrible customer service.",
    ]

    for rev in neg_reviews:
        score, label = compute_sentiment_score(rev)
        assert label == "negative", f"Expected negative for '{rev}', got {label} with score {score}"
        assert score < -0.05


def test_detect_aspects():
    """Verify aspect classification across Quality, Shipping, Service, and Value."""
    assert "Shipping & Delivery" in detect_aspects("The packaging was torn and delivery was delayed.")
    assert "Product Quality" in detect_aspects("The build material feels cheap and flimsy.")
    assert "Customer Service" in detect_aspects("Support agent was very helpful with my refund.")
    assert "Pricing & Value" in detect_aspects("Way too expensive, not worth the price.")


def test_process_reviews_dataframe():
    """Verify end-to-end review processing pipeline with metrics, aspects, and TF-IDF."""
    sample_df = pd.DataFrame([
        {"review_id": "R1", "review_text": "Great quality and fast delivery!", "rating": 5.0, "order_id": "O1"},
        {"review_id": "R2", "review_text": "Love this product, very durable.", "rating": 5.0, "order_id": "O2"},
        {"review_id": "R3", "review_text": "Arrived damaged, terrible packaging.", "rating": 1.0, "order_id": "O3"},
        {"review_id": "R4", "review_text": "Poor quality, broke immediately.", "rating": 1.0, "order_id": "O4"},
        {"review_id": "R5", "review_text": "Good value for money, affordable.", "rating": 4.0, "order_id": "O5"},
        {"review_id": "R6", "review_text": "Customer service was rude and slow.", "rating": 2.0, "order_id": "O6"},
    ])

    distribution, aspects, keywords, items = process_reviews_dataframe(
        df=sample_df,
        text_col="review_text",
        rating_col="rating",
        order_id_col="order_id",
    )

    assert distribution.total_reviews == 6
    assert distribution.positive_count >= 2
    assert distribution.negative_count >= 2
    assert distribution.avg_rating is not None
    assert len(items) == 6

    # Verify aspects are extracted
    aspect_names = [a.aspect for a in aspects]
    assert "Product Quality" in aspect_names
    assert "Shipping & Delivery" in aspect_names

    # Verify TF-IDF extracted keywords
    assert len(keywords) > 0
