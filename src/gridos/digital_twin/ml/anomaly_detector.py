"""
Anomaly detection for GridOS telemetry data.

Uses scikit-learn's Isolation Forest for unsupervised anomaly detection
on multivariate DER telemetry.  Provides ``fit``, ``predict``, and
``save``/``load`` methods for model lifecycle management.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class IsolationForestDetector:
    """Isolation Forest anomaly detector for DER telemetry.

    Parameters
    ----------
    contamination:
        Expected proportion of anomalies in the training data (0–0.5).
    n_estimators:
        Number of isolation trees.
    random_state:
        Random seed for reproducibility.
    feature_columns:
        Names of the features used (for logging and diagnostics).
    model_dir:
        Directory for persisting trained models.
    """

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 200,
        random_state: int = 42,
        feature_columns: list[str] | None = None,
        model_dir: str = "./models_cache",
    ) -> None:
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.feature_columns = feature_columns or [
            "power_kw",
            "reactive_power_kvar",
            "voltage_v",
            "current_a",
            "frequency_hz",
        ]
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self._model: Any = None
        self._sklearn_available: bool = False

        try:
            from sklearn.ensemble import IsolationForest  # noqa: F401

            self._sklearn_available = True
        except ImportError:
            logger.warning(
                "scikit-learn not installed — IsolationForestDetector will "
                "use a threshold-based fallback."
            )

    # ── Training ─────────────────────────────────────────────────────

    def fit(self, x_data: np.ndarray) -> IsolationForestDetector:
        """Fit the Isolation Forest on training data.

        Parameters
        ----------
        x_data:
            2-D array of shape ``(n_samples, n_features)``.

        Returns
        -------
        IsolationForestDetector
            ``self`` for method chaining.
        """
        if not self._sklearn_available:
            logger.warning("Skipping fit — scikit-learn not available")
            return self

        from sklearn.ensemble import IsolationForest

        self._model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self._model.fit(x_data)
        logger.info(
            "IsolationForest fitted on %d samples with %d features",
            x_data.shape[0],
            x_data.shape[1],
        )
        return self

    # ── Prediction ───────────────────────────────────────────────────

    def predict(self, x_data: np.ndarray) -> np.ndarray:
        """Predict anomalies.

        Parameters
        ----------
        x_data:
            2-D array of shape ``(n_samples, n_features)``.

        Returns
        -------
        np.ndarray
            1-D boolean array — ``True`` for anomalies.
        """
        if not self._sklearn_available or self._model is None:
            # Fallback: flag any sample with a feature > 3 std from mean
            logger.debug("Using threshold fallback for anomaly detection")
            mean = np.mean(x_data, axis=0)
            std = np.std(x_data, axis=0) + 1e-8
            z_scores = np.abs((x_data - mean) / std)
            result: np.ndarray = np.any(z_scores > 3.0, axis=1)
            return result

        labels: np.ndarray = self._model.predict(x_data)  # 1 = normal, -1 = anomaly
        result = labels == -1
        return result

    def score_samples(self, x_data: np.ndarray) -> np.ndarray:
        """Return anomaly scores (lower = more anomalous).

        Parameters
        ----------
        x_data:
            2-D array of shape ``(n_samples, n_features)``.

        Returns
        -------
        np.ndarray
            1-D array of anomaly scores.
        """
        if not self._sklearn_available or self._model is None:
            mean = np.mean(x_data, axis=0)
            std = np.std(x_data, axis=0) + 1e-8
            scores: np.ndarray = -np.max(np.abs((x_data - mean) / std), axis=1)
            return scores
        result: np.ndarray = self._model.score_samples(x_data)
        return result

    # ── Persistence ──────────────────────────────────────────────────

    def save(self, filename: str = "anomaly_detector.joblib") -> Path:
        """Save the trained model to disk."""
        path = self.model_dir / filename
        if self._model is not None:
            import joblib

            joblib.dump(
                {
                    "model": self._model,
                    "feature_columns": self.feature_columns,
                    "contamination": self.contamination,
                },
                path,
            )
            logger.info("Anomaly detector saved to %s", path)
        return path

    def load(self, filename: str = "anomaly_detector.joblib") -> None:
        """Load a trained model from disk."""
        path = self.model_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        import joblib

        data = joblib.load(path)
        self._model = data["model"]
        self.feature_columns = data.get("feature_columns", self.feature_columns)
        self.contamination = data.get("contamination", self.contamination)
        self._sklearn_available = True
        logger.info("Anomaly detector loaded from %s", path)
