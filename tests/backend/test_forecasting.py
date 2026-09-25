"""Unit tests for Sales Forecasting and Time-Series Predictive Analytics Service."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.services.forecast_service import (
    resample_daily_revenue_series,
    decompose_trend_and_seasonality,
    fit_and_forecast_models,
)


@pytest.fixture
def sample_timeseries_df():
    """Generate 90 continuous days of sales data with positive trend and strong weekend seasonality."""
    np.random.seed(42)
    start_date = datetime(2023, 1, 1)
    
    records = []
    # 90 days of transactions
    for day in range(90):
        cur_date = start_date + timedelta(days=day)
        dow = cur_date.weekday()
        
        # Base daily trend + weekend boost (Friday=4, Saturday=5)
        base = 500.0 + day * 5.0
        dow_mult = 1.6 if dow in [4, 5] else 0.85
        daily_rev = base * dow_mult + float(np.random.normal(0, 20.0))
        
        # Split into 3 orders per day
        for ord_i in range(3):
            records.append({
                "order_id": f"ORD-{day}-{ord_i}",
                "order_date": cur_date + timedelta(hours=ord_i * 4),
                "revenue": round(daily_rev / 3.0, 2),
            })
            
    return pd.DataFrame(records)


def test_resample_daily_revenue_series(sample_timeseries_df):
    """Verify daily aggregation, gap-filling, and strictly continuous frequency."""
    # Introduce an artificial missing day
    df_with_gap = sample_timeseries_df[sample_timeseries_df["order_date"].dt.day != 15].copy()
    
    daily = resample_daily_revenue_series(
        df=df_with_gap,
        date_col="order_date",
        revenue_col="revenue",
    )
    
    assert len(daily) == 90
    assert daily.isna().sum() == 0
    # Day 15 of each month (Jan, Feb, Mar) should have 0.0
    day_15 = daily[daily.index.day == 15]
    assert len(day_15) == 3
    assert (day_15 == 0.0).all()


def test_decompose_trend_and_seasonality(sample_timeseries_df):
    """Verify linear trend direction and day-of-week cyclicality detection."""
    daily = resample_daily_revenue_series(
        df=sample_timeseries_df,
        date_col="order_date",
        revenue_col="revenue",
    )
    
    decomp = decompose_trend_and_seasonality(daily)
    
    assert decomp.trend_direction == "Growing"
    assert decomp.growth_rate_pct > 0.0
    assert decomp.seasonality_detected is True
    assert decomp.seasonality_period_days == 7
    assert decomp.peak_day_of_week in ["Friday", "Saturday"]


def test_fit_and_forecast_models(sample_timeseries_df):
    """Verify model fitting, horizon projection, confidence intervals, and metrics."""
    daily = resample_daily_revenue_series(
        df=sample_timeseries_df,
        date_col="order_date",
        revenue_col="revenue",
    )
    
    horizon = 30
    conf = 0.95
    f_vals, lowers, uppers, metrics, model_name = fit_and_forecast_models(
        daily_series=daily,
        horizon_days=horizon,
        confidence_level=conf,
        model_type="auto",
    )
    
    assert len(f_vals) == horizon
    assert len(lowers) == horizon
    assert len(uppers) == horizon
    assert "Holt-Winters" in model_name or "ARIMA" in model_name or "Linear" in model_name
    
    # Check bounds geometry: lower <= predicted <= upper
    for p, l, u in zip(f_vals, lowers, uppers):
        assert l >= 0.0  # Revenue non-negativity constraint
        assert l <= p <= u
        
    # Metrics assertions
    assert metrics.mae > 0.0
    assert metrics.rmse >= metrics.mae
    assert metrics.mape is not None and metrics.mape > 0.0
