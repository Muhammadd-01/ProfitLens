"""ProfitLens MongoDB Seed Script.

Seeds MongoDB database ('profitlens') with synthetic retail operations data,
default enterprise organization, and administrative user for MongoDB Compass.

Usage:
    PYTHONPATH=backend backend/venv/bin/python data/seed_mongodb.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import pymongo
from pymongo import ASCENDING, DESCENDING, UpdateOne

# Ensure backend package can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings
from app.services.auth_service import hash_password


def get_sync_mongo_db():
    """Connect to MongoDB using configured connection URL."""
    settings = get_settings()
    mongo_url = settings.MONGODB_URL
    db_name = settings.DATABASE_NAME

    print(f"Connecting to MongoDB at: {mongo_url}")
    client = pymongo.MongoClient(
        mongo_url,
        serverSelectionTimeoutMS=5000,
        uuidRepresentation="standard",
    )
    # Ping server to confirm connection
    client.admin.command("ping")
    print(f"Successfully connected! Target database: '{db_name}'")
    return client[db_name]


def ensure_indexes(db: pymongo.database.Database) -> None:
    """Create indexes matching the ProfitLens schema for fast lookups in Compass."""
    print("Setting up MongoDB indexes...")

    # Users
    db["users"].create_index([("email", ASCENDING)], unique=True)
    db["users"].create_index([("organization_id", ASCENDING)])

    # Organizations
    db["organizations"].create_index([("slug", ASCENDING)], unique=True)

    # Datasets
    db["datasets"].create_index([("organization_id", ASCENDING)])
    db["datasets"].create_index([("created_at", DESCENDING)])

    # Customers
    db["customers"].create_index([("organization_id", ASCENDING), ("dataset_id", ASCENDING)])
    db["customers"].create_index([("external_id", ASCENDING)])
    db["customers"].create_index([("email", ASCENDING)])

    # Products
    db["products"].create_index([("organization_id", ASCENDING), ("dataset_id", ASCENDING)])
    db["products"].create_index([("external_id", ASCENDING)])
    db["products"].create_index([("category", ASCENDING)])

    # Orders
    db["orders"].create_index([("organization_id", ASCENDING), ("dataset_id", ASCENDING)])
    db["orders"].create_index([("customer_id", ASCENDING)])
    db["orders"].create_index([("order_date", DESCENDING)])

    # Reviews
    db["reviews"].create_index([("organization_id", ASCENDING), ("dataset_id", ASCENDING)])
    db["reviews"].create_index([("product_id", ASCENDING)])

    # ML Collections
    db["analysis_runs"].create_index([("dataset_id", ASCENDING)])
    db["predictions"].create_index([("dataset_id", ASCENDING)])
    db["anomalies"].create_index([("dataset_id", ASCENDING)])
    db["insights"].create_index([("dataset_id", ASCENDING)])
    db["reports"].create_index([("dataset_id", ASCENDING)])

    print("Indexes successfully verified and applied.")


def seed_database() -> None:
    """Seed default organization, demo user, synthetic dataset and collections."""
    db = get_sync_mongo_db()
    ensure_indexes(db)

    now = datetime.now(timezone.utc)
    org_id = "org-default-acme"
    user_id = "user-default-admin"
    dataset_id = "dataset-retail-synthetic"

    # 1. Seed Organization
    print("\n[1/6] Seeding default organization...")
    org_doc = {
        "_id": org_id,
        "id": org_id,
        "name": "Acme Retail Corp",
        "slug": "acme-retail-corp",
        "plan": "enterprise",
        "settings": {
            "currency": "USD",
            "timezone": "America/New_York",
            "fiscal_year_start": "January",
        },
        "created_at": now,
        "updated_at": now,
    }
    db["organizations"].update_one({"_id": org_id}, {"$set": org_doc}, upsert=True)
    print("  -> Organization 'Acme Retail Corp' ready.")

    # 2. Seed Default User (demo@profitlens.ai / password123)
    print("\n[2/6] Seeding default administrator user...")
    user_doc = {
        "_id": user_id,
        "id": user_id,
        "email": "demo@profitlens.ai",
        "password_hash": hash_password("password123"),
        "hashed_password": hash_password("password123"),
        "full_name": "Chief Analytics Officer",
        "role": "admin",
        "organization_id": org_id,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    db["users"].update_one({"_id": user_id}, {"$set": user_doc}, upsert=True)
    print("  -> User 'demo@profitlens.ai' ready (password: password123).")

    # 3. Seed Dataset Record
    print("\n[3/6] Registering synthetic omnichannel dataset...")
    synthetic_csv = PROJECT_ROOT / "data" / "synthetic" / "business_data.csv"
    csv_size = synthetic_csv.stat().st_size if synthetic_csv.exists() else 0

    dataset_doc = {
        "_id": dataset_id,
        "id": dataset_id,
        "name": "Omnichannel Retail Operations",
        "original_filename": "business_data.csv",
        "file_path": str(synthetic_csv.resolve()),
        "file_size_bytes": csv_size,
        "row_count": 30000,
        "column_count": 17,
        "file_format": "csv",
        "delimiter": ",",
        "encoding": "utf-8",
        "status": "ready",
        "error_message": None,
        "column_types": {
            "order_id": "string",
            "order_date": "datetime",
            "customer_id": "string",
            "customer_name": "string",
            "customer_email": "string",
            "region": "string",
            "customer_join_date": "datetime",
            "product_id": "string",
            "product_name": "string",
            "product_category": "string",
            "product_description": "string",
            "quantity": "integer",
            "unit_price": "float",
            "discount": "float",
            "amount": "float",
            "status": "string",
            "channel": "string",
        },
        "column_mappings": {
            "order_id": "order_id",
            "order_date": "order_date",
            "customer_id": "customer_id",
            "customer_name": "customer_name",
            "customer_email": "customer_email",
            "region": "region",
            "customer_join_date": "customer_join_date",
            "product_id": "product_id",
            "product_name": "product_name",
            "product_category": "product_category",
            "product_description": "product_description",
            "quantity": "quantity",
            "unit_price": "unit_price",
            "discount": "discount",
            "amount": "amount",
            "status": "status",
            "channel": "channel",
        },
        "organization_id": org_id,
        "created_by": user_id,
        "created_at": now,
        "updated_at": now,
    }
    db["datasets"].update_one({"_id": dataset_id}, {"$set": dataset_doc}, upsert=True)
    print("  -> Dataset 'Omnichannel Retail Operations' ready.")

    # 4. Seed Products
    products_csv = PROJECT_ROOT / "data" / "synthetic" / "products.csv"
    if products_csv.exists():
        print("\n[4/6] Seeding products collection...")
        df_products = pd.read_csv(products_csv)
        prod_ops = []
        for _, r in df_products.iterrows():
            p_id = f"prod-{r['product_id']}"
            p_doc = {
                "_id": p_id,
                "id": p_id,
                "organization_id": org_id,
                "dataset_id": dataset_id,
                "external_id": str(r["product_id"]),
                "name": str(r["name"]),
                "category": str(r["category"]),
                "unit_price": float(r["unit_price"]),
                "description": str(r["description"]),
                "total_revenue": 0.0,
                "units_sold": 0,
                "order_count": 0,
                "performance_tier": "Standard",
                "created_at": now,
            }
            prod_ops.append(UpdateOne({"_id": p_id}, {"$set": p_doc}, upsert=True))
        if prod_ops:
            db["products"].bulk_write(prod_ops)
        print(f"  -> {len(prod_ops)} products imported.")

    # 5. Seed Customers
    customers_csv = PROJECT_ROOT / "data" / "synthetic" / "customers.csv"
    if customers_csv.exists():
        print("\n[5/6] Seeding customers collection...")
        df_customers = pd.read_csv(customers_csv)
        cust_ops = []
        for _, r in df_customers.iterrows():
            c_id = f"cust-{r['customer_id']}"
            c_doc = {
                "_id": c_id,
                "id": c_id,
                "organization_id": org_id,
                "dataset_id": dataset_id,
                "external_id": str(r["customer_id"]),
                "name": str(r["name"]),
                "email": str(r["email"]),
                "region": str(r["region"]),
                "total_spent": 0.0,
                "order_count": 0,
                "first_purchase": None,
                "last_purchase": None,
                "segment": "Regular",
                "churn_risk_score": 0.15,
                "churn_risk_level": "Low",
                "estimated_clv": 500.0,
                "created_at": now,
            }
            cust_ops.append(UpdateOne({"_id": c_id}, {"$set": c_doc}, upsert=True))
        if cust_ops:
            db["customers"].bulk_write(cust_ops)
        print(f"  -> {len(cust_ops)} customers imported.")

    # 6. Seed Orders & Reviews
    orders_csv = PROJECT_ROOT / "data" / "synthetic" / "orders.csv"
    if orders_csv.exists():
        print("\n[6/6] Seeding orders collection...")
        df_orders = pd.read_csv(orders_csv)
        order_ops = []
        batch_size = 5000
        total_inserted = 0
        for _, r in df_orders.iterrows():
            o_id = f"ord-{r['order_id']}"
            o_doc = {
                "_id": o_id,
                "id": o_id,
                "organization_id": org_id,
                "dataset_id": dataset_id,
                "external_id": str(r["order_id"]),
                "customer_id": f"cust-{r['customer_id']}",
                "product_id": f"prod-{r['product_id']}",
                "order_date": str(r["order_date"]),
                "amount": float(r["amount"]),
                "discount": float(r["discount"]),
                "quantity": int(r["quantity"]),
                "status": str(r["status"]),
                "region": str(r["region"]),
                "channel": str(r["channel"]),
                "is_anomaly": False,
                "anomaly_score": None,
                "created_at": now,
            }
            order_ops.append(UpdateOne({"_id": o_id}, {"$set": o_doc}, upsert=True))
            if len(order_ops) >= batch_size:
                db["orders"].bulk_write(order_ops)
                total_inserted += len(order_ops)
                print(f"    ... processed {total_inserted} orders")
                order_ops = []
        if order_ops:
            db["orders"].bulk_write(order_ops)
            total_inserted += len(order_ops)
        print(f"  -> Total {total_inserted} orders imported.")

    reviews_csv = PROJECT_ROOT / "data" / "synthetic" / "reviews.csv"
    if reviews_csv.exists():
        print("  -> Seeding reviews collection...")
        df_reviews = pd.read_csv(reviews_csv)
        review_ops = []
        for _, r in df_reviews.iterrows():
            rv_id = f"rev-{r['review_id']}"
            rv_doc = {
                "_id": rv_id,
                "id": rv_id,
                "organization_id": org_id,
                "dataset_id": dataset_id,
                "customer_id": f"cust-{r['customer_id']}",
                "product_id": f"prod-{r['product_id']}",
                "review_text": str(r["review_text"]),
                "rating": float(r["rating"]),
                "review_date": str(r["review_date"]),
                "sentiment_score": None,
                "sentiment_label": None,
                "topics": {},
                "created_at": now,
            }
            review_ops.append(UpdateOne({"_id": rv_id}, {"$set": rv_doc}, upsert=True))
        if review_ops:
            db["reviews"].bulk_write(review_ops)
        print(f"  -> {len(review_ops)} reviews imported.")

    # Summary
    print("\n" + "=" * 60)
    print("MONGODB COMPASS SEEDING COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"Connection String : {get_settings().MONGODB_URL}")
    print(f"Database          : {db.name}")
    print("-" * 60)
    for col_name in sorted(db.list_collection_names()):
        count = db[col_name].count_documents({})
        print(f"  • {col_name:<20} : {count:>7} documents")
    print("-" * 60)
    print("Login Credentials : demo@profitlens.ai / password123")
    print("MongoDB Compass   : Open Compass and connect to:")
    print(f"                    {get_settings().MONGODB_URL}/{db.name}")
    print("=" * 60)


if __name__ == "__main__":
    seed_database()
