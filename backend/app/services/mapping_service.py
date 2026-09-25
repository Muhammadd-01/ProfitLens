"""Intelligent column mapping and schema validation engine.

DATA SCIENCE CONCEPT: SCHEMA MATCHING & FUZZY ENTITY ALIGNMENT
==============================================================

1. THE BUSINESS PROBLEM:
   Every business system formats tabular data differently:
   - Shopify exports columns: "Name", "Total", "Created at", "Email"
   - Stripe exports: "id", "amount", "created", "customer"
   - Square exports: "Transaction ID", "Gross Sales", "Date", "Customer ID"
   - Custom ERP exports: "INVOICE_NO", "NET_VAL", "TXN_DT", "ACCT_REF"

   Our downstream machine learning algorithms (ARIMA/Prophet forecasting,
   RFM K-Means clustering, XGBoost churn modeling, Isolation Forest) expect
   standardized feature vectors. Forcing users to manually rename 20 columns
   in Excel creates extreme friction. Automated schema matching eliminates this.

2. THE MATHEMATICAL CONCEPTS:

   A. Levenshtein Edit Distance:
      The minimum number of single-character edits (insertions, deletions,
      or substitutions) required to transform string s1 into s2:
          lev(s1, s2)
      We normalize this into a similarity score Sim(s1, s2) ∈ [0, 1]:
          Sim(s1, s2) = 1.0 - (lev(s1, s2) / max(len(s1), len(s2)))
      For example:
          lev("revnue", "revenue") = 1
          Sim("revnue", "revenue") = 1.0 - (1 / 7) = 0.857 (85.7% match)

   B. Jaccard Token Similarity:
      For multi-word column names (e.g. "total_order_amount" vs "order_total"):
          Tokens(s1) = {"total", "order", "amount"}
          Tokens(s2) = {"order", "total"}
          Jaccard = |Tokens(s1) ∩ Tokens(s2)| / |Tokens(s1) ∪ Tokens(s2)|
                  = 2 / 3 = 0.667

   C. Composite Semantic Match Score:
      Score(c, r) = max( PatternScore(c, r), FuzzyScore(c, r) ) * TypeCompatibility(c, r)
      - PatternScore = 1.0 for exact alias match, 0.88 for token overlap
      - FuzzyScore = Levenshtein similarity against known synonyms
      - TypeCompatibility = 1.0 if types match, 0.2 if incompatible (e.g. free text for revenue)

3. THE ALGORITHM:
   - Compare all available dataset columns against each canonical business concept
   - Select the highest-scoring candidate above the confidence threshold (0.60)
   - Resolve conflicts if two concepts claim the same dataset column (highest confidence wins)
   - Gatekeeper Validation: check which downstream Data Science modules have their minimum schema satisfied
"""

from __future__ import annotations

import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.schemas.dataset import (
    ColumnMappingSuggestion,
    ColumnMappingResponse,
    ModuleReadiness,
    SchemaValidationResult,
)
from app.utils.constants import COLUMN_PATTERNS


CANONICAL_FIELDS: List[Dict[str, Any]] = [
    {
        "field": "revenue",
        "name": "Revenue / Total Sales",
        "required": True,
        "description": "Total monetary value of the order or transaction (e.g. $45.00)",
        "expected_types": ["numeric"],
    },
    {
        "field": "order_date",
        "name": "Order Date / Timestamp",
        "required": True,
        "description": "Date or datetime when the purchase occurred (e.g. 2024-03-15)",
        "expected_types": ["datetime", "text"],
    },
    {
        "field": "customer_id",
        "name": "Customer Identifier",
        "required": True,
        "description": "Unique identifier for the buyer (enables churn and segmentation)",
        "expected_types": ["identifier", "categorical", "numeric", "text"],
    },
    {
        "field": "order_id",
        "name": "Order / Transaction ID",
        "required": True,
        "description": "Unique identifier for the order or transaction",
        "expected_types": ["identifier", "categorical", "numeric", "text"],
    },
    {
        "field": "product_id",
        "name": "Product SKU / Identifier",
        "required": False,
        "description": "Unique identifier or SKU of the purchased item",
        "expected_types": ["identifier", "categorical", "numeric", "text"],
    },
    {
        "field": "quantity",
        "name": "Quantity / Units Sold",
        "required": False,
        "description": "Number of units purchased in the transaction",
        "expected_types": ["numeric"],
    },
    {
        "field": "category",
        "name": "Product Category",
        "required": False,
        "description": "Classification group or category of the product",
        "expected_types": ["categorical", "text"],
    },
    {
        "field": "region",
        "name": "Region / Location",
        "required": False,
        "description": "Customer geographical area, state, city, or territory",
        "expected_types": ["categorical", "text"],
    },
    {
        "field": "discount",
        "name": "Discount Amount",
        "required": False,
        "description": "Discounts or promo code deductions applied to the order",
        "expected_types": ["numeric"],
    },
    {
        "field": "customer_name",
        "name": "Customer Name",
        "required": False,
        "description": "Full name or display name of the customer",
        "expected_types": ["text", "categorical"],
    },
    {
        "field": "customer_email",
        "name": "Customer Email",
        "required": False,
        "description": "Email address of the customer",
        "expected_types": ["text", "identifier"],
    },
]


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute pure Python Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def normalized_similarity(s1: str, s2: str) -> float:
    """Compute normalized similarity score in [0.0, 1.0] using Levenshtein distance."""
    str1 = re.sub(r"[^a-z0-9]", "", s1.lower())
    str2 = re.sub(r"[^a-z0-9]", "", s2.lower())

    if not str1 or not str2:
        return 0.0

    if str1 == str2:
        return 1.0

    dist = levenshtein_distance(str1, str2)
    max_len = max(len(str1), len(str2))
    return round(max(0.0, 1.0 - (dist / max_len)), 3)


def calculate_match_score(
    col_name: str,
    inferred_type: str,
    canonical_info: Dict[str, Any],
) -> Tuple[float, str]:
    """Calculate match score between a dataset column and a canonical field.
    
    Returns: (confidence_score, match_method)
    """
    canonical_field = canonical_info["field"]
    expected_types = canonical_info["expected_types"]
    clean_col = re.sub(r"[^a-z0-9]", "", col_name.lower())

    patterns = COLUMN_PATTERNS.get(canonical_field, [canonical_field])

    # 1. Exact Pattern Match
    for pattern in patterns:
        clean_pat = re.sub(r"[^a-z0-9]", "", pattern.lower())
        if clean_col == clean_pat:
            # Type compatibility check
            if inferred_type in expected_types:
                return 0.98, "exact_match"
            return 0.75, "exact_match_type_mismatch"

    # 2. Tokenized Substring Match (e.g. 'total_order_amount' contains 'amount')
    for pattern in patterns:
        clean_pat = re.sub(r"[^a-z0-9]", "", pattern.lower())
        if len(clean_pat) >= 4 and (clean_pat in clean_col or clean_col in clean_pat):
            if inferred_type in expected_types:
                return 0.88, "pattern_match"
            return 0.65, "pattern_match_type_mismatch"

    # 3. Fuzzy Levenshtein Distance against known patterns
    best_fuzzy = 0.0
    for pattern in patterns:
        clean_pat = re.sub(r"[^a-z0-9]", "", pattern.lower())
        sim = normalized_similarity(clean_col, clean_pat)
        if sim > best_fuzzy:
            best_fuzzy = sim

    if best_fuzzy >= 0.75:
        if inferred_type in expected_types:
            return round(best_fuzzy * 0.95, 2), "fuzzy_similarity"
        return round(best_fuzzy * 0.60, 2), "fuzzy_similarity_type_mismatch"

    return 0.0, "unmapped"


def generate_suggested_mappings(
    columns: List[str],
    column_profiles: Optional[List[Dict[str, Any]]] = None,
) -> List[ColumnMappingSuggestion]:
    """Generate intelligent mapping suggestions for all canonical fields."""
    type_map: Dict[str, str] = {}
    if column_profiles:
        for p in column_profiles:
            type_map[p.get("name", "")] = p.get("inferred_type", "text")

    suggestions: List[ColumnMappingSuggestion] = []
    used_columns: set[str] = set()

    # Pass 1: Find best matches for each canonical field
    field_candidates: List[Tuple[Dict[str, Any], str, float, str, List[str]]] = []

    for c_info in CANONICAL_FIELDS:
        best_col: Optional[str] = None
        best_score = 0.0
        best_method = "unmapped"
        alternatives: List[str] = []

        for col in columns:
            col_type = type_map.get(col, "text")
            score, method = calculate_match_score(col, col_type, c_info)

            if score > 0.60:
                alternatives.append(col)
                if score > best_score:
                    best_score = score
                    best_col = col
                    best_method = method

        field_candidates.append((c_info, best_col or "", best_score, best_method, alternatives))

    # Sort candidates by confidence descending so strongest matches claim columns first
    field_candidates.sort(key=lambda x: x[2], reverse=True)

    claimed_mappings: Dict[str, Tuple[Optional[str], float, str, List[str]]] = {}

    for c_info, best_col, score, method, alts in field_candidates:
        c_field = c_info["field"]
        if best_col and best_col not in used_columns and score >= 0.60:
            claimed_mappings[c_field] = (best_col, score, method, [a for a in alts if a != best_col])
            used_columns.add(best_col)
        else:
            # Fallback to remaining alternatives if top column was taken
            fallback_col = next((a for a in alts if a not in used_columns), None)
            if fallback_col:
                claimed_mappings[c_field] = (fallback_col, 0.70, "alternative_match", [])
                used_columns.add(fallback_col)
            else:
                claimed_mappings[c_field] = (None, 0.0, "unmapped", [])

    # Assemble ordered suggestions
    for c_info in CANONICAL_FIELDS:
        c_field = c_info["field"]
        mapped_col, score, method, alts = claimed_mappings.get(c_field, (None, 0.0, "unmapped", []))

        if score >= 0.85:
            conf_level = "high"
        elif score >= 0.60:
            conf_level = "medium"
        elif score > 0.0:
            conf_level = "low"
        else:
            conf_level = "unmapped"

        suggestions.append(
            ColumnMappingSuggestion(
                canonical_field=c_field,
                field_display_name=c_info["name"],
                is_required=c_info["required"],
                description=c_info["description"],
                mapped_column=mapped_col,
                confidence=score,
                confidence_level=conf_level,
                matched_by=method,
                alternative_columns=alts[:3],
            )
        )

    return suggestions


def validate_mapped_schema(mappings: Dict[str, Optional[str]]) -> SchemaValidationResult:
    """Validate which analytics modules can run based on mapped columns."""
    active_keys = {k for k, v in mappings.items() if v}

    modules = [
        {
            "module": "Executive KPIs",
            "required": ["revenue", "order_date"],
            "description": "Total revenue, order counts, and date-range trends",
        },
        {
            "module": "Sales Forecasting",
            "required": ["revenue", "order_date"],
            "description": "Predictive future revenue curves and seasonality modeling",
        },
        {
            "module": "Product Performance",
            "required": ["product_id", "revenue"],
            "description": "Pareto ABC curve, top/declining products, and category shares",
        },
        {
            "module": "Customer Segmentation (RFM)",
            "required": ["customer_id", "revenue", "order_date"],
            "description": "Recency, Frequency, Monetary clustering into actionable personas",
        },
        {
            "module": "Customer Churn Prediction",
            "required": ["customer_id", "revenue", "order_date"],
            "description": "Predicting probability of customer lapse and identifying at-risk accounts",
        },
        {
            "module": "Transaction Anomaly Detection",
            "required": ["order_id", "revenue", "order_date"],
            "description": "Flagging unusual revenue spikes and anomalous transaction values",
        },
    ]

    readiness_list: List[ModuleReadiness] = []
    ready_count = 0

    for m in modules:
        missing = [req for req in m["required"] if req not in active_keys]
        is_ready = len(missing) == 0
        if is_ready:
            ready_count += 1
            msg = f"Ready to run {m['description']}."
        else:
            missing_names = ", ".join([f.replace("_", " ").title() for f in missing])
            msg = f"Requires missing column: {missing_names}."

        readiness_list.append(
            ModuleReadiness(
                module=m["module"],
                is_ready=is_ready,
                required_fields=m["required"],
                missing_fields=missing,
                message=msg,
            )
        )

    is_basic = "revenue" in active_keys and "order_date" in active_keys
    is_ml = is_basic and "customer_id" in active_keys

    if is_ml:
        summary = "Dataset is fully configured for all Analytics and Machine Learning models."
    elif is_basic:
        summary = "Dataset is ready for Revenue Analytics and Forecasting. Map 'Customer ID' to unlock Churn & Segmentation."
    else:
        summary = "Critical fields missing. Please map at least 'Revenue' and 'Order Date' to proceed."

    return SchemaValidationResult(
        dataset_id="",
        is_valid_for_basic_analytics=is_basic,
        is_valid_for_ml=is_ml,
        module_readiness=readiness_list,
        summary_message=summary,
    )


async def get_dataset_mapping_suggestions(
    dataset_id: str,
    organization_id: str,
    db: AsyncSession,
) -> ColumnMappingResponse:
    """Retrieve or compute mapping suggestions for a dataset."""
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == uuid.UUID(dataset_id),
            Dataset.organization_id == uuid.UUID(organization_id),
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise ValueError("Dataset not found")

    # Extract available columns
    available_cols: List[str] = []
    if dataset.column_metadata and "columns" in dataset.column_metadata:
        available_cols = dataset.column_metadata["columns"]
    elif dataset.profiling_results and "columns" in dataset.profiling_results:
        available_cols = [c["name"] for c in dataset.profiling_results["columns"]]

    profiles = dataset.profiling_results.get("columns", []) if dataset.profiling_results else []

    suggestions = generate_suggested_mappings(available_cols, profiles)

    # If dataset already has saved mappings, respect user overrides
    if dataset.column_mappings:
        for s in suggestions:
            if s.canonical_field in dataset.column_mappings:
                saved_col = dataset.column_mappings[s.canonical_field]
                s.mapped_column = saved_col
                if saved_col:
                    s.confidence = 1.0
                    s.confidence_level = "high"
                    s.matched_by = "user_confirmed"

    return ColumnMappingResponse(
        dataset_id=str(dataset.id),
        mappings=suggestions,
        available_columns=available_cols,
    )


async def save_dataset_mappings(
    dataset_id: str,
    organization_id: str,
    mappings: Dict[str, Optional[str]],
    db: AsyncSession,
) -> SchemaValidationResult:
    """Save confirmed column mappings and update dataset status."""
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == uuid.UUID(dataset_id),
            Dataset.organization_id == uuid.UUID(organization_id),
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise ValueError("Dataset not found")

    # Clean empty values
    clean_mappings = {k: v for k, v in mappings.items() if v}

    dataset.column_mappings = clean_mappings
    dataset.status = "mapped"

    validation = validate_mapped_schema(clean_mappings)
    validation.dataset_id = str(dataset.id)

    await db.flush()
    return validation
