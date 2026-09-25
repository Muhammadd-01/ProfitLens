from __future__ import annotations

from enum import Enum


class DatasetStatus(str, Enum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    PROFILED = "profiled"
    MAPPING = "mapping"
    CLEANING = "cleaning"
    TRANSFORMING = "transforming"
    ENGINEERING = "engineering"
    READY = "ready"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    ERROR = "error"


class AnalysisType(str, Enum):
    FULL = "full"
    REVENUE = "revenue"
    CUSTOMERS = "customers"
    PRODUCTS = "products"
    SEGMENTATION = "segmentation"
    CHURN = "churn"
    FORECAST = "forecast"
    ANOMALY = "anomaly"
    NLP = "nlp"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class ChurnRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class AnomalySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProductPerformanceTier(str, Enum):
    TOP_PERFORMER = "top_performer"
    STRONG = "strong"
    AVERAGE = "average"
    UNDERPERFORMER = "underperformer"
    DECLINING = "declining"


class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


# Column mapping patterns for auto-detection
COLUMN_PATTERNS = {
    "customer_id": [
        "customer_id", "customerid", "customer", "client_id", "clientid",
        "client", "buyer_id", "buyerid", "buyer", "cust_id", "custid",
        "user_id", "userid", "account_id", "accountid",
    ],
    "order_id": [
        "order_id", "orderid", "order", "transaction_id", "transactionid",
        "transaction", "invoice_id", "invoiceid", "invoice", "order_number",
        "order_no", "tx_id",
    ],
    "product_id": [
        "product_id", "productid", "product", "item_id", "itemid", "item",
        "sku", "sku_id", "skuid", "product_code", "item_code",
        "product_name", "item_name",
    ],
    "order_date": [
        "order_date", "orderdate", "date", "purchase_date", "purchasedate",
        "transaction_date", "transactiondate", "created_at", "createdat",
        "invoice_date", "sale_date", "order_datetime",
    ],
    "revenue": [
        "revenue", "amount", "total", "total_amount", "totalamount",
        "sales", "price", "total_price", "totalprice", "order_total",
        "order_amount", "gross", "net_amount", "subtotal", "value",
    ],
    "quantity": [
        "quantity", "qty", "units", "count", "order_quantity",
        "items", "num_items", "pieces",
    ],
    "category": [
        "category", "product_category", "productcategory", "cat",
        "department", "dept", "group", "product_group", "type",
        "product_type", "class", "segment",
    ],
    "region": [
        "region", "area", "territory", "zone", "location", "city",
        "state", "country", "market", "store", "branch", "outlet",
    ],
    "discount": [
        "discount", "discount_amount", "discount_pct", "discount_percent",
        "coupon", "promo", "promotion",
    ],
    "status": [
        "status", "order_status", "orderstatus", "state",
    ],
    "channel": [
        "channel", "source", "medium", "platform", "sales_channel",
    ],
    "customer_name": [
        "customer_name", "name", "full_name", "fullname", "client_name",
        "buyer_name",
    ],
    "customer_email": [
        "email", "customer_email", "client_email", "e_mail", "mail",
    ],
    "review_text": [
        "review", "review_text", "comment", "feedback", "description",
        "text", "note", "remarks",
    ],
    "rating": [
        "rating", "score", "stars", "review_rating", "review_score",
    ],
}

# Minimum data thresholds for ML models
MIN_DATA_REQUIREMENTS = {
    "kpis": {"min_orders": 10},
    "revenue_analytics": {"min_orders": 50, "min_days": 7},
    "segmentation": {"min_customers": 50, "min_orders": 100, "min_days": 30},
    "churn": {"min_customers": 100, "min_orders": 500, "min_days": 90},
    "forecast": {"min_orders": 200, "min_days": 60},
    "anomaly": {"min_orders": 100, "min_days": 14},
    "nlp": {"min_reviews": 50},
}
