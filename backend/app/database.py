"""MongoDB database connection and lifecycle management for ProfitLens.

Powered by Motor (asynchronous MongoDB driver) and PyMongo.
Connects directly to MongoDB Compass compatible instances (default: mongodb://localhost:27017).
"""

from __future__ import annotations

import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import pymongo
from pymongo import ASCENDING, DESCENDING

from app.config import get_settings

logger = logging.getLogger("profitlens.database")
settings = get_settings()

_async_client: Optional[AsyncIOMotorClient] = None
_sync_client: Optional[pymongo.MongoClient] = None


def get_client() -> AsyncIOMotorClient:
    """Get or create singleton Motor async client."""
    global _async_client
    if _async_client is None:
        _async_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            uuidRepresentation="standard",
        )
    return _async_client


def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency providing the active MongoDB database."""
    client = get_client()
    return client[settings.DATABASE_NAME]


def get_sync_db() -> pymongo.database.Database:
    """Provides synchronous PyMongo database connection for scripts and CLI."""
    global _sync_client
    if _sync_client is None:
        _sync_client = pymongo.MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            uuidRepresentation="standard",
        )
    return _sync_client[settings.DATABASE_NAME]


async def init_db() -> None:
    """Initializes MongoDB database collections and performance indexes.
    
    Ensures all indexes exist so collections appear cleanly in MongoDB Compass.
    """
    db = get_db()
    logger.info("Initializing MongoDB indexes on database: %s", settings.DATABASE_NAME)

    try:
        # 1. Organizations
        await db.organizations.create_index("slug", unique=True)
        await db.organizations.create_index("id", unique=True)

        # 2. Users
        await db.users.create_index("email", unique=True)
        await db.users.create_index("organization_id")
        await db.users.create_index("id", unique=True)

        # 3. Datasets
        await db.datasets.create_index("id", unique=True)
        await db.datasets.create_index("organization_id")
        await db.datasets.create_index([("organization_id", ASCENDING), ("created_at", DESCENDING)])

        # 4. Customers
        await db.customers.create_index("id", unique=True)
        await db.customers.create_index("organization_id")
        await db.customers.create_index("dataset_id")
        await db.customers.create_index([("dataset_id", ASCENDING), ("external_id", ASCENDING)])

        # 5. Products
        await db.products.create_index("id", unique=True)
        await db.products.create_index("organization_id")
        await db.products.create_index("dataset_id")
        await db.products.create_index([("dataset_id", ASCENDING), ("external_id", ASCENDING)])

        # 6. Orders
        await db.orders.create_index("id", unique=True)
        await db.orders.create_index("organization_id")
        await db.orders.create_index("dataset_id")
        await db.orders.create_index([("dataset_id", ASCENDING), ("order_date", ASCENDING)])

        # 7. Reviews
        await db.reviews.create_index("id", unique=True)
        await db.reviews.create_index("organization_id")
        await db.reviews.create_index("dataset_id")

        # 8. Analysis Runs
        await db.analysis_runs.create_index("id", unique=True)
        await db.analysis_runs.create_index("organization_id")
        await db.analysis_runs.create_index("dataset_id")

        # 9. Predictions
        await db.predictions.create_index("id", unique=True)
        await db.predictions.create_index("organization_id")
        await db.predictions.create_index("analysis_run_id")

        # 10. Anomalies
        await db.anomalies.create_index("id", unique=True)
        await db.anomalies.create_index("organization_id")
        await db.anomalies.create_index("dataset_id")
        await db.anomalies.create_index("analysis_run_id")

        # 11. Insights
        await db.insights.create_index("id", unique=True)
        await db.insights.create_index("organization_id")
        await db.insights.create_index("dataset_id")

        # 12. Reports
        await db.reports.create_index("id", unique=True)
        await db.reports.create_index("organization_id")
        await db.reports.create_index("dataset_id")

        logger.info("MongoDB collections and indexes successfully initialized.")
    except Exception as e:
        logger.warning("Could not initialize MongoDB indexes automatically: %s", str(e))


async def close_db() -> None:
    """Closes all active database connections."""
    global _async_client, _sync_client
    if _async_client is not None:
        _async_client.close()
        _async_client = None
    if _sync_client is not None:
        _sync_client.close()
        _sync_client = None
    logger.info("MongoDB connections closed.")
