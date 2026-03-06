"""
Model training utility for GridOS ML modules.

Provides helper functions to load historical data from CSV or storage
backends, prepare datasets, and orchestrate training of the LSTM
forecaster and Isolation Forest anomaly detector.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from gridos.digital_twin.ml.anomaly_detector import IsolationForestDetector
from gridos.digital_twin.ml.forecaster import LSTMForecaster

logger = logging.getLogger(__name__)


def load_csv_timeseries(
    filepath: str,
    value_column: str = "power_kw",
    timestamp_column: str = "timestamp",
) -> pd.DataFrame:
    """Load a time-series CSV and return a sorted DataFrame.

    Parameters
    ----------
    filepath:
        Path to the CSV file.
    value_column:
        Name of the column containing the target variable.
    timestamp_column:
        Name of the timestamp column.

    Returns
    -------
    pd.DataFrame
        DataFrame sorted by timestamp with parsed datetime index.
    """
    df = pd.read_csv(filepath, parse_dates=[timestamp_column])
    df = df.sort_values(timestamp_column).reset_index(drop=True)
    logger.info(
        "Loaded %d rows from %s (columns: %s)",
        len(df),
        filepath,
        list(df.columns),
    )
    return df


def train_forecaster(
    data: np.ndarray,
    lookback: int = 96,
    horizon: int = 96,
    epochs: int = 50,
    batch_size: int = 32,
    model_dir: str = "./models_cache",
    save_model: bool = True,
) -> dict[str, Any]:
    """Train an LSTM forecaster on a 1-D time-series array.

    Parameters
    ----------
    data:
        1-D numpy array of historical values.
    lookback:
        Number of past steps for input.
    horizon:
        Number of future steps to predict.
    epochs:
        Training epochs.
    batch_size:
        Mini-batch size.
    model_dir:
        Directory for saving the model.
    save_model:
        Whether to persist the trained model.

    Returns
    -------
    dict
        Contains ``forecaster`` (the trained object) and ``history``.
    """
    forecaster = LSTMForecaster(
        lookback=lookback,
        horizon=horizon,
        model_dir=model_dir,
    )
    datasets = forecaster.prepare_data(data)
    forecaster.build_model()
    history = forecaster.fit(
        x_train=datasets["X_train"],
        y_train=datasets["y_train"],
        x_val=datasets["X_val"],
        y_val=datasets["y_val"],
        epochs=epochs,
        batch_size=batch_size,
    )
    if save_model:
        forecaster.save()
    logger.info("Forecaster training complete")
    return {"forecaster": forecaster, "history": history}


def train_anomaly_detector(
    data: np.ndarray,
    feature_columns: list[str] | None = None,
    contamination: float = 0.05,
    model_dir: str = "./models_cache",
    save_model: bool = True,
) -> dict[str, Any]:
    """Train an Isolation Forest anomaly detector.

    Parameters
    ----------
    data:
        2-D numpy array of shape ``(n_samples, n_features)``.
    feature_columns:
        Names of the feature columns.
    contamination:
        Expected anomaly fraction.
    model_dir:
        Directory for saving the model.
    save_model:
        Whether to persist the trained model.

    Returns
    -------
    dict
        Contains ``detector`` (the trained object).
    """
    detector = IsolationForestDetector(
        contamination=contamination,
        feature_columns=feature_columns,
        model_dir=model_dir,
    )
    detector.fit(data)
    if save_model:
        detector.save()
    logger.info("Anomaly detector training complete")
    return {"detector": detector}


def train_from_csv(
    csv_path: str,
    value_column: str = "power_kw",
    feature_columns: list[str] | None = None,
    model_dir: str = "./models_cache",
) -> dict[str, Any]:
    """End-to-end training pipeline from a CSV file.

    Trains both the LSTM forecaster (on ``value_column``) and the
    anomaly detector (on ``feature_columns``).

    Parameters
    ----------
    csv_path:
        Path to the CSV file.
    value_column:
        Target column for forecasting.
    feature_columns:
        Columns for anomaly detection.  Defaults to ``[value_column]``.
    model_dir:
        Directory for saving models.

    Returns
    -------
    dict
        Contains ``forecaster_result`` and ``detector_result``.
    """
    df = load_csv_timeseries(csv_path, value_column=value_column)

    # Forecaster
    values = df[value_column].values.astype(np.float32)
    fc_result = train_forecaster(values, model_dir=model_dir)

    # Anomaly detector
    if feature_columns is None:
        feature_columns = [value_column]
    available = [c for c in feature_columns if c in df.columns]
    x_features = df[available].fillna(0).values.astype(np.float32)
    ad_result = train_anomaly_detector(
        x_features, feature_columns=available, model_dir=model_dir
    )

    return {"forecaster_result": fc_result, "detector_result": ad_result}
