"""Sales Forecasting and Time-Series Predictive Analytics Service.

Statistical time-series forecasting engine utilizing Holt-Winters Exponential Smoothing,
ARIMA, and Trend-Seasonality Decomposition. Resamples daily revenue sequences,
detects weekly cyclicality, calculates predictive confidence intervals (80% & 95%),
and projects forward revenue horizons (14, 30, 60, 90 days).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import statsmodels.api as sm
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA

from app.models.dataset import Dataset
from app.schemas.ml import (
    ForecastDataPoint,
    ForecastMetrics,
    SeasonalityDecomposition,
    ForecastResponse,
)
from app.services.cleaning_service import load_dataset_as_dataframe
from app.services.mapping_service import get_dataset_mapping_suggestions


DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def resample_daily_revenue_series(
    df: pd.DataFrame,
    date_col: str,
    revenue_col: str,
) -> pd.Series:
    """Parses timestamps, groups by calendar day, fills missing dates with 0, and returns continuous Series."""
    data = df.copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce", utc=True)
    data = data.dropna(subset=[date_col, revenue_col])
    data[revenue_col] = pd.to_numeric(data[revenue_col], errors="coerce").fillna(0.0)

    # Truncate to date
    data["date_only"] = data[date_col].dt.date
    daily = data.groupby("date_only")[revenue_col].sum().sort_index()

    if daily.empty:
        return pd.Series(dtype=float)

    # Fill calendar gaps with 0
    full_idx = pd.date_range(start=daily.index.min(), end=daily.index.max(), freq="D")
    daily.index = pd.DatetimeIndex(daily.index)
    daily_reindexed = daily.reindex(full_idx, fill_value=0.0)
    daily_reindexed.name = "revenue"
    return daily_reindexed


def decompose_trend_and_seasonality(daily_series: pd.Series) -> SeasonalityDecomposition:
    """Analyzes linear trajectory and weekly day-of-week cyclicality."""
    n = len(daily_series)
    if n < 7:
        return SeasonalityDecomposition(
            trend_direction="Stable",
            growth_rate_pct=0.0,
            seasonality_detected=False,
        )

    # 1. Linear Trend via OLS
    t = np.arange(n)
    y = daily_series.values
    mean_y = float(np.mean(y)) if np.mean(y) > 0 else 1.0

    slope, intercept = np.polyfit(t, y, 1)
    annualized_growth = round(((slope * 365.0) / mean_y) * 100.0, 1)

    if annualized_growth > 5.0:
        trend_dir = "Growing"
    elif annualized_growth < -5.0:
        trend_dir = "Declining"
    else:
        trend_dir = "Stable"

    # 2. Weekly Seasonality Analysis
    dow_means = daily_series.groupby(daily_series.index.dayofweek).mean()
    peak_dow_idx = int(dow_means.idxmax())
    trough_dow_idx = int(dow_means.idxmin())

    peak_day = DAYS_OF_WEEK[peak_dow_idx]
    trough_day = DAYS_OF_WEEK[trough_dow_idx]

    max_dow_val = float(dow_means.max())
    min_dow_val = float(dow_means.min())
    seasonality_detected = (n >= 14) and (min_dow_val > 0) and ((max_dow_val / min_dow_val) >= 1.25)

    return SeasonalityDecomposition(
        trend_direction=trend_dir,
        growth_rate_pct=annualized_growth,
        seasonality_detected=seasonality_detected,
        seasonality_period_days=7 if seasonality_detected else None,
        peak_day_of_week=peak_day if seasonality_detected else None,
        trough_day_of_week=trough_day if seasonality_detected else None,
    )


def fit_and_forecast_models(
    daily_series: pd.Series,
    horizon_days: int = 30,
    confidence_level: float = 0.95,
    model_type: str = "auto",
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, ForecastMetrics, str]:
    """Fits candidate models, evaluates out-of-sample backtest, and projects forward horizon with bounds.
    
    Returns:
        forecast_values: Array of predicted values for future horizon
        lower_bounds: Array of lower confidence interval bounds
        upper_bounds: Array of upper confidence interval bounds
        metrics: Out-of-sample test metrics (MAE, RMSE, MAPE, R2)
        chosen_model_name: Name of selected model
    """
    n = len(daily_series)
    test_size = max(5, min(14, int(n * 0.2)))
    train_series = daily_series.iloc[:-test_size]
    test_series = daily_series.iloc[-test_size:]

    # Z-multiplier for confidence interval
    z_val = 1.96 if confidence_level >= 0.90 else 1.28

    # --- Candidate 1: Holt-Winters Exponential Smoothing ---
    hw_preds_test = None
    hw_model_fit = None
    try:
        use_seasonal = len(train_series) >= 14
        hw_model = ExponentialSmoothing(
            train_series,
            trend="add",
            seasonal="add" if use_seasonal else None,
            seasonal_periods=7 if use_seasonal else None,
            initialization_method="estimated",
        )
        hw_model_fit = hw_model.fit(optimized=True)
        hw_preds_test = np.maximum(0.0, hw_model_fit.forecast(steps=test_size).values)
    except Exception:
        hw_preds_test = None

    # --- Candidate 2: ARIMA ---
    arima_preds_test = None
    try:
        arima_model = ARIMA(train_series, order=(1, 1, 1))
        arima_fit = arima_model.fit()
        arima_preds_test = np.maximum(0.0, arima_fit.forecast(steps=test_size).values)
    except Exception:
        arima_preds_test = None

    # --- Candidate 3: Robust Trend + Day-of-Week Seasonality (Baseline) ---
    def fit_linear_dow(ts_train: pd.Series, steps: int) -> np.ndarray:
        t_tr = np.arange(len(ts_train))
        y_tr = ts_train.values
        slope_b, int_b = np.polyfit(t_tr, y_tr, 1)
        dow_offsets = ts_train.groupby(ts_train.index.dayofweek).mean() - np.mean(y_tr)
        
        last_d = ts_train.index[-1]
        future_dates = pd.date_range(start=last_d + timedelta(days=1), periods=steps, freq="D")
        f_t = np.arange(len(ts_train), len(ts_train) + steps)
        base_trend = int_b + slope_b * f_t
        seasonal_adds = np.array([dow_offsets.get(d.dayofweek, 0.0) for d in future_dates])
        return np.maximum(0.0, base_trend + seasonal_adds)

    linear_preds_test = fit_linear_dow(train_series, test_size)

    # Evaluate Candidate Errors on Test Set
    def evaluate_pred(preds: np.ndarray, truth: np.ndarray) -> Tuple[float, float, float, float]:
        errors = truth - preds
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        mape = float(np.mean(np.abs(errors) / np.maximum(1.0, truth)) * 100.0)
        ss_tot = float(np.sum((truth - np.mean(truth)) ** 2))
        ss_res = float(np.sum(errors ** 2))
        r2 = round(1.0 - (ss_res / ss_tot), 3) if ss_tot > 0 else 0.0
        return mae, rmse, mape, r2

    y_test = test_series.values
    hw_rmse = evaluate_pred(hw_preds_test, y_test)[1] if hw_preds_test is not None else 1e9
    arima_rmse = evaluate_pred(arima_preds_test, y_test)[1] if arima_preds_test is not None else 1e9
    linear_rmse = evaluate_pred(linear_preds_test, y_test)[1]

    # Select Champion Model
    if model_type == "holt_winters" and hw_preds_test is not None:
        chosen_type = "hw"
    elif model_type == "arima" and arima_preds_test is not None:
        chosen_type = "arima"
    elif model_type == "linear_trend":
        chosen_type = "linear"
    else:  # auto
        if hw_rmse <= arima_rmse and hw_rmse <= linear_rmse:
            chosen_type = "hw"
        elif arima_rmse <= linear_rmse:
            chosen_type = "arima"
        else:
            chosen_type = "linear"

    # Refit Champion on Full History and Project Forward
    if chosen_type == "hw":
        chosen_name = "Holt-Winters Exponential Smoothing (ETS)"
        mae, rmse, mape, r2 = evaluate_pred(hw_preds_test, y_test)
        use_seasonal = len(daily_series) >= 14
        full_model = ExponentialSmoothing(
            daily_series,
            trend="add",
            seasonal="add" if use_seasonal else None,
            seasonal_periods=7 if use_seasonal else None,
            initialization_method="estimated",
        ).fit(optimized=True)
        forecast_vals = np.maximum(0.0, full_model.forecast(steps=horizon_days).values)
        resids = full_model.resid
        sigma = float(np.std(resids)) if len(resids) > 0 else rmse
    elif chosen_type == "arima":
        chosen_name = "Auto-Regressive Integrated Moving Average (ARIMA)"
        mae, rmse, mape, r2 = evaluate_pred(arima_preds_test, y_test)
        full_fit = ARIMA(daily_series, order=(1, 1, 1)).fit()
        forecast_vals = np.maximum(0.0, full_fit.forecast(steps=horizon_days).values)
        sigma = float(np.std(full_fit.resid))
    else:
        chosen_name = "Decomposed Linear Trend & Seasonality"
        mae, rmse, mape, r2 = evaluate_pred(linear_preds_test, y_test)
        forecast_vals = fit_linear_dow(daily_series, horizon_days)
        # Empirical residual standard error from backtest
        sigma = float(rmse) if rmse > 0 else 1.0

    # Compute expanding confidence bounds
    h_idx = np.arange(1, horizon_days + 1)
    se = sigma * np.sqrt(1.0 + (h_idx / horizon_days) * 0.5)
    lower_bounds = np.maximum(0.0, forecast_vals - z_val * se)
    upper_bounds = forecast_vals + z_val * se

    metrics = ForecastMetrics(
        mae=round(mae, 2),
        rmse=round(rmse, 2),
        mape=round(mape, 1),
        r2_score=round(r2, 2),
    )

    return forecast_vals, lower_bounds, upper_bounds, metrics, chosen_name


async def run_sales_forecasting(
    dataset_id: str,
    organization_id: str,
    model_type: Optional[str] = "auto",
    horizon_days: Optional[int] = 30,
    confidence_level: Optional[float] = 0.95,
    db: Optional[AsyncSession] = None,
) -> ForecastResponse:
    """Executes full sales forecasting pipeline and saves artifacts."""
    if db is None:
        raise ValueError("Database session required")

    result = await db.execute(
        select(Dataset).where(
            Dataset.id == uuid.UUID(dataset_id),
            Dataset.organization_id == uuid.UUID(organization_id),
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} not found")

    base_dir = os.path.dirname(dataset.file_path)

    # Load cleaned or original dataset
    col_meta = dataset.column_metadata or {}
    cleaned_file = col_meta.get("cleaned_file_path")
    file_to_load = cleaned_file if cleaned_file and os.path.exists(cleaned_file) else dataset.file_path
    raw_df = load_dataset_as_dataframe(file_to_load, dataset.file_type)

    # Resolve column mappings
    mappings = dataset.column_mappings or {}
    if not mappings:
        mapping_resp = await get_dataset_mapping_suggestions(dataset_id, organization_id, db)
        mappings = {m.canonical_field: m.mapped_column for m in mapping_resp.mappings if m.mapped_column}

    date_col = mappings.get("order_date")
    rev_col = mappings.get("revenue")

    if not date_col or not rev_col:
        raise ValueError("Sales forecasting requires mapped order_date and revenue columns")

    # 1. Resample to continuous daily series
    daily_series = resample_daily_revenue_series(raw_df, date_col, rev_col)
    n_days = len(daily_series)

    if n_days < 14:
        raise ValueError(
            f"Sales forecasting requires at least 14 days of historical transactions. Found {n_days} days."
        )

    horizon = horizon_days if (horizon_days and 7 <= horizon_days <= 180) else 30
    conf = confidence_level if (confidence_level and 0.50 <= confidence_level <= 0.99) else 0.95

    # 2. Seasonality and Trend Decomposition
    seasonality = decompose_trend_and_seasonality(daily_series)

    # 3. Model Training, Selection, and Horizon Projection
    f_vals, lowers, uppers, metrics, model_name = fit_and_forecast_models(
        daily_series=daily_series,
        horizon_days=horizon,
        confidence_level=conf,
        model_type=model_type or "auto",
    )

    # 4. Construct Full Combined Time-Series Output (Historical + Forecast)
    series_points: List[ForecastDataPoint] = []

    # Historical slice
    for dt, val in daily_series.items():
        v = round(float(val), 2)
        d_str = dt.strftime("%Y-%m-%d")
        series_points.append(
            ForecastDataPoint(
                date=d_str,
                actual=v,
                predicted=v,
                lower_bound=v,
                upper_bound=v,
                is_forecast=False,
            )
        )

    # Future forecast slice
    last_hist_date = daily_series.index[-1]
    future_dates = pd.date_range(start=last_hist_date + timedelta(days=1), periods=horizon, freq="D")

    for f_date, pred, low, up in zip(future_dates, f_vals, lowers, uppers):
        series_points.append(
            ForecastDataPoint(
                date=f_date.strftime("%Y-%m-%d"),
                actual=None,
                predicted=round(float(pred), 2),
                lower_bound=round(float(low), 2),
                upper_bound=round(float(up), 2),
                is_forecast=True,
            )
        )

    # 5. Financial projections
    projected_total = round(float(np.sum(f_vals)), 2)
    prior_period_slice = daily_series.iloc[-horizon:]
    prior_total = float(prior_period_slice.sum()) if len(prior_period_slice) > 0 else 0.0

    if prior_total > 0:
        proj_growth = round(((projected_total - prior_total) / prior_total) * 100.0, 1)
    else:
        proj_growth = None

    generated_at = datetime.utcnow().isoformat()

    # 6. Save forecast CSV to disk
    forecast_csv = os.path.join(base_dir, f"{dataset.id}_sales_forecast.csv")
    export_rows = [p.model_dump() for p in series_points]
    pd.DataFrame(export_rows).to_csv(forecast_csv, index=False)

    # 7. Persist metadata into database
    col_meta["forecast_results"] = {
        "dataset_id": str(dataset.id),
        "model_name": model_name,
        "horizon_days": horizon,
        "confidence_level": conf,
        "metrics": metrics.model_dump(),
        "seasonality": seasonality.model_dump(),
        "historical_points": n_days,
        "forecast_points": horizon,
        "projected_total_revenue": projected_total,
        "projected_growth_pct": proj_growth,
        "generated_at": generated_at,
        "forecast_file_path": forecast_csv,
    }
    dataset.column_metadata = col_meta
    await db.commit()

    return ForecastResponse(
        dataset_id=str(dataset.id),
        model_name=model_name,
        horizon_days=horizon,
        confidence_level=conf,
        metrics=metrics,
        seasonality=seasonality,
        historical_points=n_days,
        forecast_points=horizon,
        series=series_points,
        projected_total_revenue=projected_total,
        projected_growth_pct=proj_growth,
        generated_at=generated_at,
    )
