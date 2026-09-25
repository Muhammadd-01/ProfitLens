from __future__ import annotations

import pytest
from app.services.mapping_service import (
    levenshtein_distance,
    normalized_similarity,
    generate_suggested_mappings,
    validate_mapped_schema,
)


def test_levenshtein_distance_and_similarity():
    """Verify Levenshtein edit distance and normalized similarity."""
    # Identical
    assert levenshtein_distance("revenue", "revenue") == 0
    assert normalized_similarity("revenue", "revenue") == 1.0

    # Single insertion/deletion typo
    assert levenshtein_distance("revnue", "revenue") == 1
    assert normalized_similarity("revnue", "revenue") > 0.80

    # Completely different strings
    assert normalized_similarity("customer", "product") < 0.35


def test_generate_suggested_mappings_shopify_style():
    """Verify auto-mapping on real-world Shopify-style column headers."""
    columns = [
        "Order ID",
        "Total",
        "Created at",
        "Customer ID",
        "Lineitem sku",
        "Quantity",
        "Shipping City",
    ]
    suggestions = generate_suggested_mappings(columns)

    mapping_dict = {s.canonical_field: s.mapped_column for s in suggestions}

    assert mapping_dict["order_id"] == "Order ID"
    assert mapping_dict["revenue"] == "Total"
    assert mapping_dict["order_date"] == "Created at"
    assert mapping_dict["customer_id"] == "Customer ID"
    assert mapping_dict["product_id"] == "Lineitem sku"
    assert mapping_dict["quantity"] == "Quantity"


def test_generate_suggested_mappings_erp_style():
    """Verify auto-mapping on cryptic enterprise ERP column headers."""
    columns = [
        "TXN_ID",
        "TOTAL_SALES",
        "TXN_DATE",
        "BUYER_ID",
        "ITEM_CODE",
    ]
    suggestions = generate_suggested_mappings(columns)
    mapping_dict = {s.canonical_field: s.mapped_column for s in suggestions}

    assert mapping_dict["order_id"] == "TXN_ID"
    assert mapping_dict["revenue"] == "TOTAL_SALES"
    assert mapping_dict["order_date"] == "TXN_DATE"
    assert mapping_dict["customer_id"] == "BUYER_ID"
    assert mapping_dict["product_id"] == "ITEM_CODE"


def test_validate_mapped_schema_readiness():
    """Verify schema gatekeeper correctly gates downstream modules."""
    # 1. Empty mappings -> cannot run anything
    empty_res = validate_mapped_schema({})
    assert empty_res.is_valid_for_basic_analytics is False
    assert empty_res.is_valid_for_ml is False

    # 2. Basic schema -> KPIs + Forecasting ready, Churn not ready
    basic_res = validate_mapped_schema({
        "revenue": "sales",
        "order_date": "date",
    })
    assert basic_res.is_valid_for_basic_analytics is True
    assert basic_res.is_valid_for_ml is False
    kpis_mod = next(m for m in basic_res.module_readiness if m.module == "Executive KPIs")
    assert kpis_mod.is_ready is True
    churn_mod = next(m for m in basic_res.module_readiness if m.module == "Customer Churn Prediction")
    assert churn_mod.is_ready is False
    assert "customer_id" in churn_mod.missing_fields

    # 3. Full schema -> All ready
    full_res = validate_mapped_schema({
        "order_id": "order_id",
        "revenue": "sales",
        "order_date": "date",
        "customer_id": "cust_id",
        "product_id": "sku",
    })
    assert full_res.is_valid_for_basic_analytics is True
    assert full_res.is_valid_for_ml is True
    assert all(m.is_ready for m in full_res.module_readiness)
