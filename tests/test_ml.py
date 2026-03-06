"""
Tests for GridOS machine learning modules.
"""

from __future__ import annotations

import numpy as np

from gridos.digital_twin.ml.anomaly_detector import IsolationForestDetector
from gridos.digital_twin.ml.forecaster import LSTMForecaster


class TestLSTMForecaster:
    """Tests for the LSTM forecaster."""

    def test_prepare_data(self, sample_timeseries):
        forecaster = LSTMForecaster(lookback=96, horizon=96)
        datasets = forecaster.prepare_data(sample_timeseries)
        assert "X_train" in datasets
        assert "y_train" in datasets
        assert datasets["X_train"].shape[1] == 96
        assert datasets["X_train"].shape[2] == 1

    def test_persistence_fallback(self, sample_timeseries):
        forecaster = LSTMForecaster(lookback=96, horizon=96)
        recent = sample_timeseries[-96:]
        prediction = forecaster.predict(recent)
        assert len(prediction) == 96
        # Persistence: all values should equal the last input
        assert np.all(prediction == recent[-1])

    def test_scaler(self, sample_timeseries):
        forecaster = LSTMForecaster(lookback=96, horizon=96)
        forecaster.prepare_data(sample_timeseries)
        assert forecaster._scaler_min <= forecaster._scaler_max


class TestIsolationForestDetector:
    """Tests for the anomaly detector."""

    def test_fit_and_predict(self):
        np.random.seed(42)
        normal = np.random.randn(200, 3)
        anomalies = np.random.randn(10, 3) * 5 + 10
        x_data = np.vstack([normal, anomalies])

        detector = IsolationForestDetector(contamination=0.05)
        detector.fit(x_data)
        predictions = detector.predict(x_data)

        assert len(predictions) == len(x_data)
        assert predictions.dtype == bool

    def test_score_samples(self):
        np.random.seed(42)
        x_data = np.random.randn(100, 3)
        detector = IsolationForestDetector()
        detector.fit(x_data)
        scores = detector.score_samples(x_data)
        assert len(scores) == 100

    def test_fallback_without_sklearn(self):
        """Test threshold-based fallback."""
        detector = IsolationForestDetector()
        detector._sklearn_available = False
        detector._model = None

        np.random.seed(42)
        x_data = np.random.randn(100, 3)
        # Add an obvious outlier
        x_data[0] = [100, 100, 100]

        predictions = detector.predict(x_data)
        assert predictions[0] is True or predictions[0] == True  # noqa: E712
