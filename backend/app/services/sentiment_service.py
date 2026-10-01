"""Customer Review & Sentiment Intelligence Service.

Performs natural language processing (NLP) on customer reviews:
lexicon-based polarity & compound scoring, negation & intensifier resolution,
Aspect-Based Sentiment Analysis (Product Quality, Shipping, Service, Value),
and TF-IDF keyword extraction.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.dataset import Dataset
from app.schemas.ml import (
    SentimentReviewItem,
    AspectSentiment,
    KeywordItem,
    SentimentDistribution,
    SentimentOverviewResponse,
)
from app.services.cleaning_service import load_dataset_as_dataframe
from app.services.mapping_service import get_dataset_mapping_suggestions


# Commercial Valence Lexicon
VALENCE_LEXICON: Dict[str, float] = {
    # High Positive
    "excellent": 3.6, "exceptional": 3.7, "superb": 3.5, "outstanding": 3.6, "fantastic": 3.5,
    "love": 3.4, "perfect": 3.3, "awesome": 3.2, "wonderful": 3.3, "brilliant": 3.1,
    "exceeded": 3.0, "delighted": 3.2, "thrilled": 3.3, "spectacular": 3.5, "stellar": 3.4,
    # Moderate Positive
    "great": 2.8, "good": 2.0, "satisfied": 2.4, "worth": 2.2, "recommend": 2.6,
    "happy": 2.5, "fast": 2.0, "quick": 1.8, "durable": 2.3, "sturdy": 2.2,
    "helpful": 2.2, "easy": 1.8, "nice": 1.9, "solid": 1.8, "smooth": 1.9,
    "pleased": 2.2, "reliable": 2.4, "beautiful": 2.7, "handy": 1.7, "bargain": 2.1,
    "affordable": 1.8, "five": 1.5, "stars": 1.5, "penny": 0.8,
    # High Negative
    "terrible": -3.6, "horrible": -3.7, "awful": -3.5, "disaster": -3.8, "scam": -3.9,
    "fraud": -3.9, "worst": -3.8, "abysmal": -3.7, "useless": -3.2, "garbage": -3.4,
    "trash": -3.3, "unacceptable": -3.4, "ruined": -3.2, "hate": -3.3,
    # Moderate Negative
    "poor": -2.6, "broken": -3.2, "damaged": -3.0, "disappointed": -2.8, "disappointing": -2.7,
    "slow": -2.0, "late": -2.2, "bad": -2.2, "cheap": -1.8, "flimsy": -2.4,
    "defect": -2.8, "defective": -3.0, "rude": -3.0, "waste": -2.9, "delayed": -2.1,
    "missing": -2.4, "overpriced": -2.2, "expensive": -1.5, "broke": -2.8,
    "refund": -1.6, "return": -1.2, "problem": -1.9, "error": -1.8, "fail": -2.4,
    "failed": -2.5, "scratch": -1.8, "scratched": -2.0, "issue": -1.5, "difficult": -1.8,
}

NEGATIONS = {
    "not", "never", "no", "hardly", "barely", "neither", "nor", "without",
    "didnt", "didn't", "dont", "don't", "wont", "won't", "cant", "can't",
    "cannot", "isnt", "isn't", "wasnt", "wasn't", "couldnt", "couldn't",
}

INTENSIFIERS: Dict[str, float] = {
    "very": 1.4, "extremely": 1.8, "incredibly": 1.8, "super": 1.4,
    "highly": 1.4, "really": 1.3, "completely": 1.4, "absolutely": 1.6,
    "totally": 1.4, "so": 1.2, "quite": 1.1, "barely": 0.5, "somewhat": 0.7,
}

# Aspect domain keyword dictionaries
ASPECT_DICTIONARIES: Dict[str, List[str]] = {
    "Product Quality": [
        "quality", "durable", "broken", "defect", "defective", "material", "build",
        "fabric", "sturdy", "broke", "cheap", "flimsy", "finish", "fit", "size",
        "color", "design", "works", "solid", "scratch", "ruined", "look",
    ],
    "Shipping & Delivery": [
        "shipping", "delivery", "arrive", "arrived", "package", "packaging",
        "late", "box", "carrier", "tracked", "fast", "quick", "delay", "delayed",
        "damaged", "transit", "dispatch", "courier", "time", "speed",
    ],
    "Customer Service": [
        "service", "support", "agent", "refund", "response", "helpful", "rude",
        "rep", "warranty", "return", "contact", "email", "answer", "staff",
        "call", "polite", "courteous", "assist", "assistance",
    ],
    "Pricing & Value": [
        "price", "expensive", "cheap", "worth", "value", "cost", "dollar",
        "penny", "deal", "overpriced", "affordable", "money", "bargain",
        "discount", "pricey", "rate", "fee", "charge",
    ],
}


def clean_text_tokens(text: str) -> List[str]:
    """Tokenizes text while stripping punctuation."""
    if not isinstance(text, str):
        return []
    words = re.findall(r"\b[a-zA-Z']+\b", text.lower())
    return words


def compute_sentiment_score(text: str) -> Tuple[float, str]:
    """Computes normalized compound sentiment score [-1.0, 1.0] and categorical label."""
    words = clean_text_tokens(text)
    if not words:
        return 0.0, "neutral"

    scores = []
    i = 0
    while i < len(words):
        word = words[i]
        val = VALENCE_LEXICON.get(word, 0.0)

        if val != 0.0:
            # Check preceding tokens for negations and intensifiers (window of 2)
            negated = False
            multiplier = 1.0

            start_idx = max(0, i - 2)
            for prev in words[start_idx:i]:
                if prev in NEGATIONS:
                    negated = True
                elif prev in INTENSIFIERS:
                    multiplier *= INTENSIFIERS[prev]

            final_val = val * multiplier
            if negated:
                final_val = final_val * -0.75  # Negation flip and discount

            scores.append(final_val)
        i += 1

    if not scores:
        return 0.0, "neutral"

    raw_sum = sum(scores)
    # VADER-style hyperbolic normalization: sum / sqrt(sum^2 + alpha)
    compound = round(float(raw_sum / np.sqrt((raw_sum ** 2) + 15.0)), 3)

    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return compound, label


def detect_aspects(text: str) -> List[str]:
    """Classifies which business aspects are mentioned in a review."""
    words = set(clean_text_tokens(text))
    matched_aspects = []

    for aspect_name, keywords in ASPECT_DICTIONARIES.items():
        if any(kw in words for kw in keywords):
            matched_aspects.append(aspect_name)

    return matched_aspects if matched_aspects else ["General Experience"]


def extract_keywords_tfidf(
    reviews: List[str],
    sentiments: List[str],
    top_n: int = 15,
) -> List[KeywordItem]:
    """Extracts top unigram and bigram keywords with TF-IDF and sentiment attribution."""
    if not reviews or len(reviews) < 3:
        return []

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=100,
            min_df=2,
        )
        X = vectorizer.fit_transform(reviews)
        feature_names = vectorizer.get_feature_names_out()
        tfidf_means = np.asarray(X.mean(axis=0)).ravel()

        # Count frequencies and sentiment breakdown
        top_indices = tfidf_means.argsort()[::-1][:top_n]
        keyword_items: List[KeywordItem] = []

        for idx in top_indices:
            term = str(feature_names[idx])
            mean_tfidf = round(float(tfidf_means[idx]), 3)

            # Check sentiment occurrences
            pos_c, neg_c, neu_c = 0, 0, 0
            term_c = 0
            for r_text, r_sent in zip(reviews, sentiments):
                if term in r_text.lower():
                    term_c += 1
                    if r_sent == "positive":
                        pos_c += 1
                    elif r_sent == "negative":
                        neg_c += 1
                    else:
                        neu_c += 1

            if term_c == 0:
                continue

            if pos_c > neg_c:
                assigned_sent = "positive"
            elif neg_c > pos_c:
                assigned_sent = "negative"
            else:
                assigned_sent = "neutral"

            keyword_items.append(
                KeywordItem(
                    keyword=term,
                    frequency=term_c,
                    tfidf_score=mean_tfidf,
                    sentiment=assigned_sent,
                )
            )

        return keyword_items
    except Exception:
        return []


def process_reviews_dataframe(
    df: pd.DataFrame,
    text_col: str,
    rating_col: Optional[str] = None,
    order_id_col: Optional[str] = None,
    customer_id_col: Optional[str] = None,
    product_id_col: Optional[str] = None,
    date_col: Optional[str] = None,
    sample_limit: int = 500,
) -> Tuple[SentimentDistribution, List[AspectSentiment], List[KeywordItem], List[SentimentReviewItem]]:
    """Runs complete sentiment, aspect breakdown, and keyword extraction over reviews dataframe."""
    data = df.dropna(subset=[text_col]).copy()
    if len(data) == 0:
        raise ValueError("No text reviews found in dataset.")

    # Limit to reasonable sample size if massive
    if len(data) > sample_limit:
        data = data.sample(sample_limit, random_state=42).reset_index(drop=True)

    items: List[SentimentReviewItem] = []
    texts_list = []
    sentiments_list = []
    pos_c, neu_c, neg_c = 0, 0, 0
    compound_scores = []
    ratings = []

    aspect_buckets: Dict[str, Dict[str, Any]] = {
        asp: {"total": 0, "pos": 0, "neu": 0, "neg": 0, "scores": []}
        for asp in list(ASPECT_DICTIONARIES.keys()) + ["General Experience"]
    }

    for idx, row in data.iterrows():
        raw_text = str(row[text_col]).strip()
        if not raw_text:
            continue

        comp_score, sent_label = compute_sentiment_score(raw_text)
        aspects = detect_aspects(raw_text)

        compound_scores.append(comp_score)
        texts_list.append(raw_text)
        sentiments_list.append(sent_label)

        if sent_label == "positive":
            pos_c += 1
        elif sent_label == "negative":
            neg_c += 1
        else:
            neu_c += 1

        for asp in aspects:
            if asp in aspect_buckets:
                aspect_buckets[asp]["total"] += 1
                aspect_buckets[asp]["scores"].append(comp_score)
                if sent_label == "positive":
                    aspect_buckets[asp]["pos"] += 1
                elif sent_label == "negative":
                    aspect_buckets[asp]["neg"] += 1
                else:
                    aspect_buckets[asp]["neu"] += 1

        r_val = float(row[rating_col]) if rating_col and rating_col in row and pd.notna(row[rating_col]) else None
        if r_val is not None:
            ratings.append(r_val)

        c_id = str(row[customer_id_col]) if customer_id_col and customer_id_col in row and pd.notna(row[customer_id_col]) else None
        p_id = str(row[product_id_col]) if product_id_col and product_id_col in row and pd.notna(row[product_id_col]) else None
        o_id = str(row[order_id_col]) if order_id_col and order_id_col in row and pd.notna(row[order_id_col]) else None
        o_date = str(row[date_col]) if date_col and date_col in row and pd.notna(row[date_col]) else None

        items.append(
            SentimentReviewItem(
                id=str(row.get("review_id", f"REV-{idx}")),
                customer_id=c_id,
                product_id=p_id,
                order_id=o_id,
                order_date=o_date,
                rating=r_val,
                review_text=raw_text,
                sentiment_label=sent_label,
                sentiment_score=comp_score,
                aspect_tags=aspects,
            )
        )

    total = len(items)
    avg_compound = round(float(np.mean(compound_scores)), 2) if compound_scores else 0.0
    net_sentiment = round(((pos_c - neg_c) / max(1, total)) * 100.0, 1)
    avg_rating = round(float(np.mean(ratings)), 1) if ratings else None

    distribution = SentimentDistribution(
        positive_count=pos_c,
        neutral_count=neu_c,
        negative_count=neg_c,
        total_reviews=total,
        avg_compound_score=avg_compound,
        net_sentiment_score=net_sentiment,
        avg_rating=avg_rating,
    )

    # Compile aspects
    aspect_list: List[AspectSentiment] = []
    for asp, stats in aspect_buckets.items():
        if stats["total"] > 0:
            asp_avg = round(float(np.mean(stats["scores"])), 2) if stats["scores"] else 0.0
            if asp_avg >= 0.10:
                asp_label = "mostly_positive"
            elif asp_avg <= -0.10:
                asp_label = "mostly_negative"
            else:
                asp_label = "mixed"

            # Top terms for this aspect
            kws = ASPECT_DICTIONARIES.get(asp, [])
            top_terms = [k for k in kws if any(k in t.lower() for t in texts_list)][:4]

            aspect_list.append(
                AspectSentiment(
                    aspect=asp,
                    total_mentions=stats["total"],
                    positive_mentions=stats["pos"],
                    neutral_mentions=stats["neu"],
                    negative_mentions=stats["neg"],
                    avg_sentiment_score=asp_avg,
                    sentiment_label=asp_label,
                    top_terms=top_terms,
                )
            )

    aspect_list = sorted(aspect_list, key=lambda x: x.total_mentions, reverse=True)

    # TF-IDF Keywords
    keywords = extract_keywords_tfidf(texts_list, sentiments_list, top_n=15)

    return distribution, aspect_list, keywords, items


async def run_customer_sentiment_analysis(
    dataset_id: str,
    organization_id: str,
    db: Optional[AsyncIOMotorDatabase] = None,
) -> SentimentOverviewResponse:
    """Orchestrates sentiment analysis over dataset reviews or attached synthetic review data in MongoDB."""
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

    base_dir = os.path.dirname(dataset.file_path)

    # 1. Check if dataset itself has review text column
    col_meta = dataset.column_metadata or {}
    cleaned_file = col_meta.get("cleaned_file_path")
    file_to_load = cleaned_file if cleaned_file and os.path.exists(cleaned_file) else dataset.file_path
    raw_df = load_dataset_as_dataframe(file_to_load, dataset.file_type)

    # Resolve column mappings
    mappings = dataset.column_mappings or {}
    if not mappings:
        mapping_resp = await get_dataset_mapping_suggestions(dataset_id, organization_id, db)
        mappings = {m.canonical_field: m.mapped_column for m in mapping_resp.mappings if m.mapped_column}

    text_col = mappings.get("review_text")
    rating_col = mappings.get("rating")
    ord_col = mappings.get("order_id")
    cust_col = mappings.get("customer_id")
    prod_col = mappings.get("product_id")
    date_col = mappings.get("order_date")

    # If active dataset does not have review text, fallback to project synthetic reviews if available
    reviews_df = raw_df
    if not text_col or text_col not in raw_df.columns:
        # Check standard synthetic review file
        synthetic_review_path = os.path.join(os.getcwd(), "data", "synthetic", "reviews.csv")
        if os.path.exists(synthetic_review_path):
            reviews_df = pd.read_csv(synthetic_review_path)
            text_col = "review_text"
            rating_col = "rating"
            ord_col = "order_id"
            cust_col = "customer_id"
            prod_col = "product_id"
            date_col = "review_date"
        else:
            raise ValueError(
                "Dataset does not contain a mapped 'review_text' column. Please map customer review text to run NLP sentiment analysis."
            )

    # 2. Execute NLP pipeline
    distribution, aspects, keywords, items = process_reviews_dataframe(
        df=reviews_df,
        text_col=text_col,
        rating_col=rating_col,
        order_id_col=ord_col,
        customer_id_col=cust_col,
        product_id_col=prod_col,
        date_col=date_col,
    )

    gen_time = datetime.utcnow().isoformat()

    # 3. Cache results in dataset metadata
    col_meta["sentiment_analysis"] = {
        "dataset_id": str(dataset.id),
        "total_reviews": distribution.total_reviews,
        "net_sentiment_score": distribution.net_sentiment_score,
        "distribution": distribution.model_dump(),
        "analyzed_at": gen_time,
    }
    await db.datasets.update_one(
        {"$or": [{"id": dataset.id}, {"_id": dataset.id}]},
        {"$set": {
            "column_metadata": col_meta,
            "updated_at": datetime.utcnow(),
        }}
    )

    return SentimentOverviewResponse(
        dataset_id=str(dataset.id),
        distribution=distribution,
        aspects=aspects,
        top_keywords=keywords,
        recent_reviews=items[:100],  # Return up to 100 recent for UI table
        analyzed_at=gen_time,
    )
